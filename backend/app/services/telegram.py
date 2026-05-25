"""Telegram bot integration — webhook and missing-info questions."""
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.missing_info import MissingInfoRequest


def telegram_status() -> dict:
    settings = get_settings()
    if not settings.telegram_configured:
        return {
            "configured": False,
            "status": "not_configured",
            "message": "Telegram not configured — set TELEGRAM_BOT_TOKEN",
        }
    return {
        "configured": True,
        "status": "ready",
        "message": "Telegram bot token present — set webhook after deploy",
    }


async def send_message(chat_id: str, text: str) -> dict:
    settings = get_settings()
    if not settings.telegram_configured:
        return {"success": False, "message": "Telegram not configured"}
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        if resp.status_code == 200:
            return {"success": True, "message": "Message sent"}
        return {"success": False, "message": resp.text}


async def send_missing_info_question(db: Session, request_id: int, chat_id: str) -> dict:
    req = db.query(MissingInfoRequest).filter(MissingInfoRequest.id == request_id).first()
    if not req:
        return {"success": False, "message": "Request not found"}
    text = f"ScholarHive AI — Missing info:\n\n{req.question}\n\nReply to this message with your answer."
    result = await send_message(chat_id, text)
    if result.get("success"):
        req.status = "pending"
        db.commit()
    return result


def handle_webhook_update(db: Session, update: dict) -> dict:
    settings = get_settings()
    if not settings.telegram_configured:
        return {"ok": True, "message": "Telegram not configured — webhook ignored"}

    message = update.get("message") or update.get("edited_message")
    if not message or "text" not in message:
        return {"ok": True, "message": "No text message"}

    text = message["text"].strip()
    reply_to = message.get("reply_to_message", {}).get("message_id")
    pending = (
        db.query(MissingInfoRequest)
        .filter(MissingInfoRequest.status == "pending")
        .order_by(MissingInfoRequest.created_at.desc())
        .all()
    )
    target = pending[0] if pending else None
    if target:
        target.user_reply = text
        target.status = "answered"
        target.answered_at = datetime.utcnow()
        if reply_to:
            target.telegram_message_id = str(reply_to)
        db.commit()
        return {"ok": True, "message": "Reply saved for review", "request_id": target.id}
    return {"ok": True, "message": "Reply received — no pending question matched"}
