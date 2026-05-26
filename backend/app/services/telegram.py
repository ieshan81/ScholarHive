"""Telegram bot integration — send, diagnostics, webhook."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.missing_info import MissingInfoRequest

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
BOT_USERNAME_HINT = "Scholarhivebot"


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
        "message": "Telegram bot token present",
    }


def token_format_valid() -> bool:
    settings = get_settings()
    token = (settings.telegram_bot_token or "").strip()
    if not token:
        return False
    return bool(re.match(r"^\d+:[A-Za-z0-9_-]{20,}$", token))


async def _api_call(method: str, payload: dict | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.telegram_configured:
        return {"ok": False, "error_code": 0, "description": "Telegram not configured"}
    url = TELEGRAM_API.format(token=settings.telegram_bot_token.strip(), method=method)
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload or {})
            data = resp.json()
            if not isinstance(data, dict):
                return {"ok": False, "error_code": resp.status_code, "description": resp.text[:500]}
            if resp.status_code != 200 and "description" not in data:
                data["description"] = resp.text[:500]
                data["error_code"] = data.get("error_code", resp.status_code)
            return data
    except httpx.TimeoutException:
        return {"ok": False, "error_code": 408, "description": "Telegram API timeout"}
    except httpx.RequestError as exc:
        return {"ok": False, "error_code": 0, "description": f"Network error: {exc}"}


def map_telegram_error(error_code: int | None, description: str) -> dict[str, Any]:
    desc = (description or "").lower()
    next_step = "Check Railway TELEGRAM_BOT_TOKEN and try again."
    message = description or "Telegram API error"

    if error_code == 401 or "unauthorized" in desc:
        message = "Invalid or rotated bot token."
        next_step = "Update TELEGRAM_BOT_TOKEN in Railway with the token from @BotFather, then redeploy."
    elif error_code == 403 or "blocked" in desc:
        message = "Bot cannot message this chat — user may have blocked the bot or not pressed Start."
        next_step = f"Open t.me/{BOT_USERNAME_HINT}, press Start, then send test again."
    elif error_code == 400 and ("chat not found" in desc or "chat_id" in desc):
        message = "Chat not found — wrong chat ID or bot has not received /start from this user."
        next_step = f"Message @{BOT_USERNAME_HINT} and send /start, then save the correct numeric chat ID."
    elif error_code == 409 or "conflict" in desc:
        message = "Webhook/getUpdates conflict — bot may already use a webhook elsewhere."
        next_step = "Use one webhook URL for this bot (ScholarHive /api/telegram/webhook) or clear webhook in BotFather."
    elif error_code == 408 or "timeout" in desc:
        message = "Telegram request timed out."
        next_step = "Retry in a moment. If it persists, check Railway network and Telegram status."
    elif error_code == 0 and "network" in desc:
        message = "Could not reach Telegram API."
        next_step = "Retry shortly. Check Railway outbound network."

    return {
        "success": False,
        "message": message,
        "telegram_error_code": error_code,
        "telegram_error_description": description,
        "next_step": next_step,
    }


async def send_message(chat_id: str, text: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.telegram_configured:
        return {**map_telegram_error(0, "not configured"), "message": "Telegram not configured — set TELEGRAM_BOT_TOKEN"}
    if not chat_id or not str(chat_id).strip():
        return {
            "success": False,
            "message": "No chat ID provided.",
            "telegram_error_code": None,
            "telegram_error_description": "missing chat_id",
            "next_step": "Save your numeric Telegram chat ID first.",
        }

    data = await _api_call("sendMessage", {"chat_id": str(chat_id).strip(), "text": text[:4096]})
    if data.get("ok"):
        return {
            "success": True,
            "message": "Message sent successfully.",
            "telegram_message_id": (data.get("result") or {}).get("message_id"),
        }
    return map_telegram_error(data.get("error_code"), data.get("description", "Unknown Telegram error"))


async def get_bot_info() -> dict[str, Any]:
    data = await _api_call("getMe")
    if data.get("ok"):
        return {"ok": True, "username": (data.get("result") or {}).get("username"), "id": (data.get("result") or {}).get("id")}
    return {"ok": False, "error_code": data.get("error_code"), "description": data.get("description")}


async def get_webhook_info() -> dict[str, Any]:
    data = await _api_call("getWebhookInfo")
    if data.get("ok"):
        return {"ok": True, "webhook": data.get("result") or {}}
    return {"ok": False, "error_code": data.get("error_code"), "description": data.get("description")}


async def run_diagnostics(db: Session) -> dict[str, Any]:
    from app.services import telegram_config as tg_cfg

    settings = get_settings()
    cfg = tg_cfg.get_config(db)
    out: dict[str, Any] = {
        "telegram_configured": settings.telegram_configured,
        "chat_id_saved": bool(cfg.chat_id),
        "token_format_valid": token_format_valid() if settings.telegram_configured else False,
        "get_me_ok": False,
        "bot_username": None,
        "webhook_url": None,
        "webhook_pending_update_count": 0,
        "webhook_conflict_hint": None,
        "last_test_status": cfg.last_test_status,
        "last_test_message": cfg.last_test_message,
        "last_error_code": getattr(cfg, "last_error_code", None),
        "last_error_description": getattr(cfg, "last_error_description", None),
        "checks": [],
    }

    if not settings.telegram_configured:
        out["checks"].append({"name": "bot_token", "ok": False, "detail": "TELEGRAM_BOT_TOKEN not set"})
        return out

    if not out["token_format_valid"]:
        out["checks"].append({"name": "token_format", "ok": False, "detail": "Token format looks invalid (expected digits:secret)"})
    else:
        out["checks"].append({"name": "token_format", "ok": True, "detail": "Token format OK (not exposed)"})

    me = await get_bot_info()
    if me.get("ok"):
        out["get_me_ok"] = True
        out["bot_username"] = me.get("username")
        out["checks"].append({"name": "getMe", "ok": True, "detail": f"Bot @{me.get('username')}"})
    else:
        out["checks"].append({
            "name": "getMe",
            "ok": False,
            "detail": me.get("description", "getMe failed"),
            "error_code": me.get("error_code"),
        })

    wh = await get_webhook_info()
    if wh.get("ok"):
        info = wh.get("webhook") or {}
        out["webhook_url"] = info.get("url") or None
        out["webhook_pending_update_count"] = info.get("pending_update_count", 0)
        if info.get("last_error_message"):
            out["webhook_conflict_hint"] = info.get("last_error_message")
        out["checks"].append({
            "name": "webhook",
            "ok": True,
            "detail": f"Webhook: {out['webhook_url'] or 'not set'}",
        })
    else:
        out["checks"].append({"name": "webhook", "ok": False, "detail": wh.get("description", "getWebhookInfo failed")})

    if not cfg.chat_id:
        out["checks"].append({"name": "chat_id", "ok": False, "detail": "No chat ID saved"})
    else:
        out["checks"].append({"name": "chat_id", "ok": True, "detail": "Chat ID saved (value hidden)"})

    return out


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
