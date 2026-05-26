from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.services import gmail as gmail_service
from app.services import gmail_scanner

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return gmail_service.gmail_status(db)


@router.get("/auth-url")
def auth_url():
    return gmail_service.get_auth_url()


@router.get("/callback")
def callback(code: str | None = Query(None), db: Session = Depends(get_db)):
    settings = get_settings()
    if not code:
        return {"success": False, "message": "Missing authorization code"}
    result = gmail_service.save_tokens_from_code(db, code)
    if result.get("success"):
        return RedirectResponse(f"{settings.public_app_url.rstrip('/')}/gmail?connected=1")
    return result


@router.get("/messages")
def list_messages(status: str | None = None, db: Session = Depends(get_db)):
    return gmail_scanner.list_gmail_messages(db, status)


@router.get("/messages/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db)):
    from app.models.gmail_message import GmailMessage
    import json

    m = db.query(GmailMessage).filter(GmailMessage.id == message_id).first()
    if not m:
        raise HTTPException(404, "Message not found")
    return {
        "id": m.id,
        "subject": m.subject,
        "sender": m.sender,
        "snippet": m.snippet,
        "body_text": m.body_text,
        "links": json.loads(m.links_json or "[]"),
        "classification": m.classification,
        "classification_reason": m.classification_reason,
        "status": m.status,
        "gmail_url": f"https://mail.google.com/mail/u/0/#inbox/{m.gmail_id}",
    }


@router.post("/scan")
async def scan(days: int = 30, db: Session = Depends(get_db)):
    return await gmail_scanner.scan_gmail_v2(db, days=days)


@router.post("/messages/{message_id}/reject")
def reject_message(message_id: int, db: Session = Depends(get_db)):
    from app.models.gmail_message import GmailMessage

    m = db.query(GmailMessage).filter(GmailMessage.id == message_id).first()
    if m:
        m.status = "rejected"
        m.classification = "irrelevant"
        db.commit()
    return {"message": "Rejected"}
