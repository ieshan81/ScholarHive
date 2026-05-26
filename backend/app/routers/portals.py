from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.portal import Portal
from app.services.portal_agent import open_portal_session, save_session_stub, portal_agent_status
from app.services.portal_cleanup import cleanup_portal_domains

router = APIRouter(prefix="/api/portals", tags=["portals"])


@router.get("")
def list_portals(show_tracking: bool = Query(False), db: Session = Depends(get_db)):
    cleanup_portal_domains(db)
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
        }
        for p in portals
    ]


@router.post("/cleanup-domains")
def cleanup(db: Session = Depends(get_db)):
    return cleanup_portal_domains(db)


@router.get("/agent-status")
def agent_status():
    return portal_agent_status()


@router.post("/{portal_id}/open-session")
def open_session(portal_id: int, db: Session = Depends(get_db)):
    return open_portal_session(db, portal_id)


class SaveSessionBody(BaseModel):
    portal_account_id: int
    note: str = "user_confirmed_session"


@router.post("/save-session")
def save_session(body: SaveSessionBody, db: Session = Depends(get_db)):
    return save_session_stub(db, body.portal_account_id, body.note)
