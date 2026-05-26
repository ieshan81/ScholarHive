from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.portal import Portal
from app.services.portal_agent import open_portal_session, save_session_stub, portal_agent_status

router = APIRouter(prefix="/api/portals", tags=["portals"])


@router.get("")
def list_portals(db: Session = Depends(get_db)):
    portals = db.query(Portal).order_by(Portal.source_count.desc()).all()
    return [
        {
            "id": p.id,
            "domain": p.domain,
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
