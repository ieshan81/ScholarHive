from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.services import telegram as telegram_service
from app.services import telegram_config as tg_config

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class ChatIdBody(BaseModel):
    chat_id: str


class SendTestRequest(BaseModel):
    chat_id: str | None = None
    message: str = "ScholarHive AI test message — Telegram is configured."


class SendQuestionRequest(BaseModel):
    request_id: int
    chat_id: str | None = None


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    cfg = tg_config.get_config(db)
    return {
        "chat_id": cfg.chat_id,
        "chat_id_saved": bool(cfg.chat_id),
        "last_test_at": cfg.last_test_at.isoformat() if cfg.last_test_at else None,
        "last_test_status": cfg.last_test_status,
        "last_test_message": cfg.last_test_message,
        "last_error_code": cfg.last_error_code,
        "last_error_description": cfg.last_error_description,
    }


@router.get("/diagnostics")
async def diagnostics(db: Session = Depends(get_db)):
    return await telegram_service.run_diagnostics(db)


@router.put("/config")
def put_config(body: ChatIdBody, db: Session = Depends(get_db)):
    return tg_config.save_chat_id(db, body.chat_id)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    base = telegram_service.telegram_status()
    cfg = tg_config.get_config(db)
    base["chat_id_saved"] = bool(cfg.chat_id)
    base["last_test_status"] = cfg.last_test_status
    return base


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
async def send_test(body: SendTestRequest | None = None, db: Session = Depends(get_db)):
    chat_id = body.chat_id if body else None
    message = body.message if body else None
    return await tg_config.send_test(db, chat_id, message)


@router.post("/send-question")
async def send_question(body: SendQuestionRequest, db: Session = Depends(get_db)):
    chat_id = body.chat_id or tg_config.get_chat_id(db)
    if not chat_id:
        return {"success": False, "message": "Save Telegram chat ID in settings first"}
    return await telegram_service.send_missing_info_question(db, body.request_id, chat_id)
