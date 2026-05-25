"""Optional dev-only seed — never runs in production."""
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.profile import Profile


def seed_database(db: Session) -> None:
    settings = get_settings()
    if settings.is_production or not settings.should_seed_demo:
        if not db.query(Profile).filter(Profile.id == 1).first():
            db.add(Profile(
                id=1,
                major="Mechanical Engineering",
                international_student=True,
            ))
            db.commit()
        return

    # Dev-only demo seed (ENABLE_DEMO_DATA=true in development)
    from datetime import date, timedelta
    from app.models.story import Story
    from app.models.scholarship import Scholarship
    from app.models.essay import Essay
    from app.models.missing_info import MissingInfoRequest
    from app.models.document import Document

    if db.query(Scholarship).filter(Scholarship.is_demo.is_(True)).first():
        return

    if not db.query(Profile).filter(Profile.id == 1).first():
        db.add(Profile(
            id=1,
            university="Sample University",
            major="Mechanical Engineering",
            international_student=True,
            visa_status="F-1",
            gpa=3.6,
        ))

    db.add(Story(
        title="[DEV] FSAE Brake System",
        category="engineering project",
        summary="Dev sample story",
        verified_by_user=True,
        is_demo=True,
    ))
    db.add(Scholarship(
        name="[DEV DEMO] Sample Scholarship",
        source_type="demo",
        source_url="https://example.com/dev",
        is_demo=True,
        status="found",
    ))
    db.commit()
