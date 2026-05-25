from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.services import gmail as gmail_service

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


@router.post("/scan")
async def scan(db: Session = Depends(get_db)):
    return await gmail_service.scan_gmail(db)
