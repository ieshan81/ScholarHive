from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.portal import Portal
from app.services.portal_cleanup import cleanup_portal_domains
from app.services.portal_agent import (
    cleanup_session,
    continue_after_checkpoint,
    get_run,
    list_opportunities,
    open_portal_session,
    portal_agent_status,
    save_session_for_run,
    save_session_stub,
    scan_public_portal,
    scan_with_session,
    start_browser_session,
)
from app.services import portal_browser as browser

router = APIRouter(prefix="/api/portals", tags=["portals"])


@router.get("")
def list_portals(show_tracking: bool = Query(False), db: Session = Depends(get_db)):
    cleanup_portal_domains(db)
    agent = portal_agent_status()
    q = db.query(Portal).order_by(Portal.source_count.desc())
    if not show_tracking:
        q = q.filter(Portal.domain_status == "active")
    portals = q.all()
    return [
        {
            "id": p.id,
            "domain": p.domain,
            "canonical_domain": p.canonical_domain or p.domain,
            "domain_status": p.domain_status,
            "portal_name": p.portal_name,
            "portal_url": p.portal_url,
            "source_count": p.source_count,
            "login_required": p.login_required,
            "session_status": p.session_status,
            "last_scanned_at": p.last_scanned_at.isoformat() if p.last_scanned_at else None,
            "opportunities_discovered": p.opportunities_discovered,
            "checkpoints_pending": p.checkpoints_pending,
            "playwright_available": agent.get("chromium_available"),
        }
        for p in portals
    ]


@router.post("/cleanup-domains")
def cleanup(db: Session = Depends(get_db)):
    return cleanup_portal_domains(db)


@router.get("/agent-status")
def agent_status():
    return portal_agent_status()


@router.post("/{portal_id}/start-browser-session")
def start_browser(portal_id: int, db: Session = Depends(get_db)):
    return start_browser_session(db, portal_id)


@router.post("/{portal_id}/open-session")
def open_session(portal_id: int, db: Session = Depends(get_db)):
    return open_portal_session(db, portal_id)


@router.post("/{portal_id}/scan-public")
def scan_public(portal_id: int, db: Session = Depends(get_db)):
    return scan_public_portal(db, portal_id)


@router.post("/{portal_id}/scan-with-session")
def scan_session(portal_id: int, db: Session = Depends(get_db)):
    return scan_with_session(db, portal_id)


@router.post("/runs/{run_id}/continue-after-checkpoint")
def continue_checkpoint(run_id: int, db: Session = Depends(get_db)):
    return continue_after_checkpoint(db, run_id)


@router.post("/runs/{run_id}/save-session")
def save_run_session(run_id: int, db: Session = Depends(get_db)):
    return save_session_for_run(db, run_id)


@router.get("/runs/{run_id}")
def get_run_state(run_id: int, db: Session = Depends(get_db)):
    data = get_run(db, run_id)
    if not data:
        raise HTTPException(404, "Run not found")
    return data


@router.get("/runs/{run_id}/screenshot")
def get_screenshot(run_id: int, db: Session = Depends(get_db)):
    from app.models.portal import PortalRun

    run = db.query(PortalRun).filter(PortalRun.id == run_id).first()
    path_str = None
    if run and run.latest_screenshot_path:
        path_str = run.latest_screenshot_path
    if not path_str:
        path_str = str(browser.screenshot_path(run_id))
    path = Path(path_str)
    if not path.is_file():
        raise HTTPException(404, "Screenshot not available yet")
    return FileResponse(path, media_type="image/png")


@router.get("/{portal_id}/opportunities")
def portal_opportunities(portal_id: int, db: Session = Depends(get_db)):
    return list_opportunities(db, portal_id)


@router.post("/{portal_id}/cleanup-session")
def cleanup_portal_session(portal_id: int, db: Session = Depends(get_db)):
    return cleanup_session(db, portal_id)


class SaveSessionBody(BaseModel):
    portal_account_id: int
    note: str = "manual_session"


@router.post("/save-session")
def save_session(body: SaveSessionBody, db: Session = Depends(get_db)):
    return save_session_stub(db, body.portal_account_id, body.note)
