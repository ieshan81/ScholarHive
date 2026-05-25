from sqlalchemy.orm import Query
from app.config import get_settings


def exclude_demo(query: Query, model) -> Query:
    """Hide demo/mock rows unless explicit dev flag is enabled."""
    settings = get_settings()
    if settings.enable_demo_data and not settings.is_production:
        return query
    if hasattr(model, "is_demo"):
        return query.filter(model.is_demo.is_(False))
    return query
