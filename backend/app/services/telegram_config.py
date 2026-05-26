from datetime import datetime
from sqlalchemy.orm import Session
from app.models.telegram_config import TelegramUserConfig
from app.services import telegram as telegram_service


def get_config(db: Session) -> TelegramUserConfig:
    cfg = db.query(TelegramUserConfig).filter(TelegramUserConfig.id == 1).first()
    if not cfg:
        cfg = TelegramUserConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def save_chat_id(db: Session, chat_id: str) -> dict:
    cfg = get_config(db)
    cfg.chat_id = chat_id.strip()
    cfg.updated_at = datetime.utcnow()
    db.commit()
    return {"saved": True, "chat_id": cfg.chat_id}


def get_chat_id(db: Session) -> str | None:
    cfg = db.query(TelegramUserConfig).filter(TelegramUserConfig.id == 1).first()
    return cfg.chat_id if cfg else None


def _record_test_result(cfg: TelegramUserConfig, result: dict) -> None:
    cfg.last_test_at = datetime.utcnow()
    cfg.last_test_status = "success" if result.get("success") else "failed"
    cfg.last_test_message = result.get("message")
    cfg.last_error_code = result.get("telegram_error_code")
    cfg.last_error_description = result.get("telegram_error_description")


async def send_test(db: Session, chat_id: str | None = None, message: str | None = None) -> dict:
    cid = (chat_id or get_chat_id(db) or "").strip()
    if not cid:
        result = {
            "success": False,
            "message": "No chat ID saved — enter and save your Telegram chat ID first.",
            "telegram_error_code": None,
            "telegram_error_description": "missing chat_id",
            "next_step": "Save your numeric chat ID from @userinfobot or after messaging your bot.",
        }
        cfg = get_config(db)
        _record_test_result(cfg, result)
        db.commit()
        return result

    text = message or "ScholarHive AI test — your chat ID is saved and messaging works."
    result = await telegram_service.send_message(cid, text)
    cfg = get_config(db)
    _record_test_result(cfg, result)
    db.commit()
    return {**result, "chat_id_saved": bool(get_chat_id(db))}
