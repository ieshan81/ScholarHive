from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db, check_database_connection
from app.services import gmail as gmail_service
from app.services import telegram as telegram_service
from app.services.web_search import web_search_status

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/status")
def settings_status(db: Session = Depends(get_db)):
    settings = get_settings()
    gmail = gmail_service.gmail_status(db)
    telegram = telegram_service.telegram_status()
    web = web_search_status(db)
    db_ok = check_database_connection()
    storage = settings.storage_writable

    return {
        "database": {
            "configured": bool(settings.database_url),
            "status": "connected" if db_ok else "connection_failed",
            "message": "Database reachable" if db_ok else "Check DATABASE_URL",
        },
        "gemini": {
            "configured": settings.gemini_configured,
            "status": "configured" if settings.gemini_configured else "not_configured",
            "message": "GEMINI_API_KEY set" if settings.gemini_configured else "Add GEMINI_API_KEY for essay drafts",
        },
        "web_search": {
            "configured": settings.tavily_configured,
            "status": web.get("status", "not_configured"),
            "message": web.get("message"),
            "last_run": web.get("last_run"),
        },
        "gmail": {
            "configured": gmail.get("configured", False),
            "status": gmail.get("status", "not_configured"),
            "message": gmail.get("message"),
            "connected": gmail.get("connected", False),
            "redirect_uri": settings.google_redirect_uri,
        },
        "telegram": {
            "configured": telegram.get("configured", False),
            "status": telegram.get("status", "not_configured"),
            "message": telegram.get("message"),
        },
        "storage": {
            "configured": True,
            "status": "writable" if storage else "metadata_only",
            "message": (
                f"Upload path {settings.upload_storage_path} is writable"
                if storage
                else "Metadata-only — mount Railway volume at /data for persistent uploads"
            ),
            "driver": settings.upload_storage_driver,
            "path": settings.upload_storage_path,
        },
        "production": {
            "configured": settings.is_production,
            "status": "production" if settings.is_production else "development",
            "message": f"Public URL default: {settings.public_app_url}",
        },
        "demo_data": {
            "configured": False,
            "status": "disabled",
            "message": "Demo/mock data disabled in production",
        },
        "human_approval": {
            "configured": True,
            "status": "enforced",
            "message": "No auto-submit — human approval required",
        },
        "background_jobs": {
            "configured": False,
            "status": "manual_triggers_only",
            "message": "Run Web Search, Gmail scan, and eligibility from UI",
        },
    }
