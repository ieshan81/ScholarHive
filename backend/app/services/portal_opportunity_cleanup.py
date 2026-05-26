"""Reclassify portal opportunities and mark junk portal domains."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.portal import Portal, PortalOpportunity
from app.services.opportunity_quality import classify_portal_link
from app.services.portal_domain import is_blocked_domain, quick_canonical_domain

KNOWN_JUNK_PORTAL_DOMAINS = frozenset({
    "go.anything.com",
    "ablink.r.sofi.com",
    "post.spmailtechno.com",
    "linkedin.com",
    "itunes.apple.com",
    "apps.apple.com",
    "play.google.com",
})

DONATE_ONLY_PORTALS = frozenset({
    "islamicity.org",
})


def _portal_should_be_ignored(portal: Portal) -> str | None:
    domain = (portal.domain or "").lower().replace("www.", "")
    canonical = (portal.canonical_domain or domain or "").lower().replace("www.", "")
    url = (portal.portal_url or "").lower()

    if domain in KNOWN_JUNK_PORTAL_DOMAINS or canonical in KNOWN_JUNK_PORTAL_DOMAINS:
        return "tracking"
    if is_blocked_domain(domain) or is_blocked_domain(canonical):
        return "tracking"
    if domain in DONATE_ONLY_PORTALS and ("/donate" in url or "donation" in url):
        return "irrelevant"
    if "linkedin.com" in domain or "linkedin.com" in url:
        return "irrelevant"
    return None


def _reclassify_opportunity(opp: PortalOpportunity) -> str:
    ctx = ""
    if opp.eligibility_summary:
        ctx = opp.eligibility_summary
    elif opp.extracted_fields_json and isinstance(opp.extracted_fields_json, dict):
        ctx = str(opp.extracted_fields_json.get("context", ""))

    result = classify_portal_link(
        opp.title or "",
        opp.portal_url or opp.application_url or "",
        ctx,
        final_url=opp.portal_url or opp.application_url,
    )
    opp.link_classification = result["classification"]
    opp.quality_score = result["confidence"]
    opp.quality_reason = result["reason"]
    opp.canonical_url = result.get("canonical_url")

    if result["save"]:
        opp.quality_status = "accepted"
    elif result["confidence"] >= 45 and result["classification"] == "unknown":
        opp.quality_status = "needs_review"
    else:
        opp.quality_status = "rejected"
    return opp.quality_status


def cleanup_opportunities(db: Session) -> dict:
    reviewed = accepted = rejected = needs_review = 0
    portals_marked = 0

    for portal in db.query(Portal).all():
        ignore_status = _portal_should_be_ignored(portal)
        if ignore_status and portal.domain_status == "active":
            portal.domain_status = ignore_status
            portals_marked += 1
        elif not ignore_status and portal.domain_status in ("tracking", "irrelevant"):
            canonical = quick_canonical_domain(portal.portal_url) or portal.domain
            if canonical and not is_blocked_domain(canonical) and canonical not in KNOWN_JUNK_PORTAL_DOMAINS:
                portal.domain_status = "active"
                portal.canonical_domain = canonical

    for opp in db.query(PortalOpportunity).all():
        reviewed += 1
        status = _reclassify_opportunity(opp)
        if status == "accepted":
            accepted += 1
        elif status == "needs_review":
            needs_review += 1
        else:
            rejected += 1

    from app.models.portal import PortalAccount

    # Recalculate accepted counts per portal
    for portal in db.query(Portal).all():
        account_ids = [
            a.id for a in db.query(PortalAccount).filter(PortalAccount.portal_id == portal.id).all()
        ]
        if account_ids:
            count = (
                db.query(PortalOpportunity)
                .filter(
                    PortalOpportunity.portal_account_id.in_(account_ids),
                    PortalOpportunity.quality_status == "accepted",
                )
                .count()
            )
            portal.opportunities_discovered = count

    db.commit()
    return {
        "opportunities_reviewed": reviewed,
        "accepted": accepted,
        "rejected": rejected,
        "needs_review": needs_review,
        "portals_marked_ignored": portals_marked,
    }
