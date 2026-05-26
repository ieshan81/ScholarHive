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


async def send_test(db: Session, chat_id: str | None = None) -> dict:
    cid = chat_id or get_chat_id(db)
    if not cid:
        return {"success": False, "message": "No chat ID saved — enter and save your Telegram chat ID first"}
    result = await telegram_service.send_message(cid, "ScholarHive AI test — your chat ID is saved and working.")
    cfg = get_config(db)
    cfg.last_test_at = datetime.utcnow()
    cfg.last_test_status = "success" if result.get("success") else "failed"
    cfg.last_test_message = result.get("message")
    db.commit()
    return {**result, "chat_id": cid}
