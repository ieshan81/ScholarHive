from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db, check_database_connection
from app.services import gmail as gmail_service
from app.services import telegram as telegram_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/status")
def settings_status(db: Session = Depends(get_db)):
    settings = get_settings()
    gmail = gmail_service.gmail_status(db)
    telegram = telegram_service.telegram_status()
    db_ok = check_database_connection()

    return {
        "gmail": {
            "configured": gmail.get("configured", False),
            "status": gmail.get("status", "not_configured"),
            "message": gmail.get("message"),
            "connected": gmail.get("connected", False),
        },
        "telegram": {
            "configured": telegram.get("configured", False),
            "status": telegram.get("status", "not_configured"),
            "message": telegram.get("message"),
        },
        "gemini": {
            "configured": settings.gemini_configured,
            "status": "configured" if settings.gemini_configured else "needs_environment_variable",
            "message": "GEMINI_API_KEY set" if settings.gemini_configured else "Add GEMINI_API_KEY",
        },
        "database": {
            "configured": bool(settings.database_url),
            "status": "connected" if db_ok else "connection_failed",
            "message": "Database reachable" if db_ok else "Check DATABASE_URL",
        },
        "railway": {
            "configured": settings.environment == "production",
            "status": "production_ready" if settings.environment == "production" else "development",
            "message": "Set ENVIRONMENT=production on Railway",
        },
        "human_approval": {
            "configured": True,
            "status": "enforced",
            "message": "All submissions require manual human approval",
        },
        "background_jobs": {
            "configured": False,
            "status": "manual_triggers_only",
            "message": "Use UI buttons to scan Gmail, recalculate eligibility, etc.",
        },
    }
