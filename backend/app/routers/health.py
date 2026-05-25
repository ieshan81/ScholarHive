from fastapi import APIRouter
from app.config import get_settings
from app.database import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    settings = get_settings()
    db_ok = check_database_connection()
    return {
        "status": "ok",
        "service": "ScholarHive AI",
        "database": "connected" if db_ok else "not_connected",
        "gemini_configured": settings.gemini_configured,
        "tavily_configured": settings.tavily_configured,
        "gmail_configured": settings.gmail_configured,
        "telegram_configured": settings.telegram_configured,
        "environment": settings.environment,
        "demo_data_enabled": settings.enable_demo_data and not settings.is_production,
    }
