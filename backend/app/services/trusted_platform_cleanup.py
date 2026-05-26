"""Apply trusted platform cleanup across portals, opportunities, and scholarships."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.portal import Portal, PortalAccount, PortalOpportunity
from app.models.scholarship import Scholarship
from app.models.discovery import DiscoveryCandidate
from app.services.portal_opportunity_cleanup import _reclassify_opportunity
from app.services.trusted_platforms import (
    DEFAULT_BLOCKED_DOMAINS,
    is_trusted_domain,
    trusted_only_enabled,
    trusted_mode_status,
)


def _ensure_blocked_sources(db: Session) -> None:
    from app.models.trusted_platform import BlockedSource

    for domain, reason in DEFAULT_BLOCKED_DOMAINS.items():
        existing = db.query(BlockedSource).filter(BlockedSource.domain == domain).first()
        if not existing:
            db.add(BlockedSource(domain=domain, reason=reason, status="blocked"))


def apply_trusted_platform_cleanup(db: Session) -> dict:
    _ensure_blocked_sources(db)
    portals_ignored = 0
    opportunities_rejected = 0
    scholarships_hidden = 0

    trusted_active = 0
    for portal in db.query(Portal).all():
        if is_trusted_domain(portal.canonical_domain or portal.domain, db):
            if portal.domain_status != "active":
                portal.domain_status = "active"
            platform = None
            from app.services.trusted_platforms import get_platform_for_url

            plat = get_platform_for_url(portal.portal_url or f"https://{portal.domain}", db)
            if plat:
                portal.platform_key = plat["platform_key"]
            trusted_active += 1
        else:
            if portal.domain_status == "active":
                portal.domain_status = "ignored"
                portals_ignored += 1

    from app.services.trusted_platforms import _host_from_url

    for opp in db.query(PortalOpportunity).all():
        url = opp.canonical_url or opp.portal_url or opp.application_url
        host = _host_from_url(url)
        if not host or not is_trusted_domain(host, db):
            if opp.quality_status == "accepted":
                opp.quality_status = "rejected"
                opp.quality_reason = "Not in trusted platform mode"
                opportunities_rejected += 1
            continue
        _reclassify_opportunity(opp)

    for sch in db.query(Scholarship).filter(Scholarship.is_demo.is_(False)).all():
        domain = sch.portal_domain
        if not domain and sch.source_url:
            from app.services.portal_domain import quick_canonical_domain

            domain = quick_canonical_domain(sch.source_url)
        if sch.user_edited:
            sch.visibility_status = "active"
            continue
        if sch.status in ("submitted", "won", "in_progress"):
            continue
        if not is_trusted_domain(domain, db):
            if getattr(sch, "visibility_status", "active") != "hidden":
                sch.visibility_status = "hidden"
                if not sch.reject_reason:
                    sch.reject_reason = "Not in trusted platform mode"
                scholarships_hidden += 1
        elif sch.source_type == "gmail" and trusted_only_enabled():
            if getattr(sch, "visibility_status", "active") != "hidden":
                sch.visibility_status = "hidden"
                sch.reject_reason = sch.reject_reason or "Gmail discovery paused in trusted mode"
                scholarships_hidden += 1

    for cand in db.query(DiscoveryCandidate).filter(DiscoveryCandidate.extraction_status == "pending").all():
        if cand.source_url and not is_trusted_domain(cand.domain, db):
            cand.extraction_status = "rejected"
            cand.classification_reason = "Not in trusted platform mode"

    for portal in db.query(Portal).all():
        account_ids = [
            a.id for a in db.query(PortalAccount).filter(PortalAccount.portal_id == portal.id).all()
        ]
        if account_ids:
            portal.opportunities_discovered = (
                db.query(PortalOpportunity)
                .filter(
                    PortalOpportunity.portal_account_id.in_(account_ids),
                    PortalOpportunity.quality_status == "accepted",
                )
                .count()
            )

    db.commit()
    mode = trusted_mode_status(db)
    return {
        "trusted_portals_active": trusted_active,
        "portals_ignored": portals_ignored,
        "opportunities_rejected": opportunities_rejected,
        "scholarships_hidden": scholarships_hidden,
        "gmail_auto_discovery_paused": mode["gmail_auto_discovery_paused"],
        "trusted_only_mode": mode["trusted_only_mode"],
        "platforms": mode["platforms"],
    }
