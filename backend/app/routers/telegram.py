from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.services import telegram as telegram_service

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class SendTestRequest(BaseModel):
    chat_id: str
    message: str = "ScholarHive AI test message — Telegram is configured."


class SendQuestionRequest(BaseModel):
    request_id: int
    chat_id: str


@router.get("/status")
def status():
    return telegram_service.telegram_status()


@router.post("/webhook")
async def webhook(
    update: dict,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    settings = get_settings()
    if not settings.telegram_configured:
        return {"ok": True, "message": "Telegram not configured"}
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(403, "Invalid webhook secret")
    return telegram_service.handle_webhook_update(db, update)


@router.post("/send-test")
async def send_test(body: SendTestRequest):
    return await telegram_service.send_message(body.chat_id, body.message)


@router.post("/send-question")
async def send_question(body: SendQuestionRequest, db: Session = Depends(get_db)):
    return await telegram_service.send_missing_info_question(db, body.request_id, body.chat_id)
