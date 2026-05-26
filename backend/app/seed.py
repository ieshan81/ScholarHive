"""Optional dev-only seed — never runs in production."""
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.profile import Profile


def seed_trusted_platforms(db: Session) -> None:
    from app.models.trusted_platform import TrustedPlatform, BlockedSource
    from app.services.trusted_platforms import DEFAULT_PLATFORMS, DEFAULT_BLOCKED_DOMAINS

    for p in DEFAULT_PLATFORMS:
        existing = db.query(TrustedPlatform).filter(TrustedPlatform.platform_key == p["platform_key"]).first()
        if not existing:
            db.add(
                TrustedPlatform(
                    name=p["name"],
                    platform_key=p["platform_key"],
                    allowed_domains_json=p["allowed_domains"],
                    status=p["status"],
                    login_required=p.get("login_required", "unknown"),
                    notes="Official ScholarHive trusted platform",
                )
            )
    for domain, reason in DEFAULT_BLOCKED_DOMAINS.items():
        if not db.query(BlockedSource).filter(BlockedSource.domain == domain).first():
            db.add(BlockedSource(domain=domain, reason=reason, status="blocked"))

    from app.models.portal import Portal

    for p in DEFAULT_PLATFORMS:
        primary = p["allowed_domains"][0]
        portal = db.query(Portal).filter(Portal.domain == primary).first()
        if not portal:
            db.add(
                Portal(
                    domain=primary,
                    canonical_domain=primary,
                    domain_status="active",
                    portal_name=p["name"],
                    portal_url=f"https://{primary}",
                    platform_key=p["platform_key"],
                )
            )
        else:
            portal.domain_status = "active"
            portal.platform_key = p["platform_key"]
            portal.portal_name = p["name"]
    db.commit()


def seed_database(db: Session) -> None:
    settings = get_settings()
    seed_trusted_platforms(db)
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
