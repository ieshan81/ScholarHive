"""Mark junk portal domains as tracking/blocked without deleting rows."""
from sqlalchemy.orm import Session

from app.models.portal import Portal
from app.services.portal_domain import is_blocked_domain, quick_canonical_domain


def cleanup_portal_domains(db: Session) -> dict:
    updated = 0
    for portal in db.query(Portal).all():
        canonical = quick_canonical_domain(portal.portal_url) or portal.domain
        if is_blocked_domain(portal.domain) or is_blocked_domain(canonical):
            if portal.domain_status != "tracking":
                portal.domain_status = "tracking"
                updated += 1
            continue
        if canonical and canonical != portal.domain:
            portal.canonical_domain = canonical
            portal.domain_status = "active"
            updated += 1
        elif portal.domain_status not in ("active", "tracking"):
            portal.domain_status = "active"
    db.commit()
    return {"updated": updated, "message": f"Portal cleanup: {updated} records adjusted"}
