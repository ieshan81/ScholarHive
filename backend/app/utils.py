from sqlalchemy.orm import Query
from app.config import get_settings


def exclude_demo(query: Query, model) -> Query:
    settings = get_settings()
    if settings.enable_demo_data and not settings.is_production:
        return query
    if hasattr(model, "is_demo"):
        return query.filter(model.is_demo.is_(False))
    return query


def filter_radar_scholarships(query: Query, include_leads: bool = False, review_only: bool = False) -> Query:
    """Hide rejected/duplicate/source-page junk from default Radar."""
    from app.models.scholarship import Scholarship
    from app.config import get_settings

    if review_only:
        return query.filter(
            Scholarship.status.in_(("needs_review", "source_page_only", "found"))
        )
    q = query.filter(Scholarship.status.notin_(("rejected", "duplicate")))
    if not include_leads:
        q = q.filter(Scholarship.status != "source_page_only")
    if get_settings().trusted_only_mode and hasattr(Scholarship, "visibility_status"):
        q = q.filter(Scholarship.visibility_status == "active")
    return q
