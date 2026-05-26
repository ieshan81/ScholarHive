"""Discovery pipeline: candidate → classify → extract → verify → save/reject."""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.discovery import DiscoveryRun, DiscoveryCandidate
from app.models.scholarship import Scholarship
from app.models.portal import Portal
from app.services.discovery_classifier import (
    classify_candidate,
    extract_domain,
    should_save_as_scholarship,
    should_extract_from_page,
)
from app.services.discovery_helpers import (
    normalize_url,
    make_dedupe_key,
    trust_heuristics,
    merge_missing_fields,
    parse_deadline,
    structure_candidates_with_gemini,
)


def get_or_create_portal(db: Session, url: str | None, name: str | None = None) -> Portal | None:
    from app.services.portal_domain import quick_canonical_domain
    from app.services.trusted_platforms import get_platform_for_url, should_create_portal

    ok, _reason = should_create_portal(url, db)
    if not ok:
        domain = quick_canonical_domain(url)
        if domain:
            portal = db.query(Portal).filter(Portal.domain == domain).first()
            if portal and portal.domain_status == "active":
                portal.domain_status = "ignored"
        return None

    domain = quick_canonical_domain(url)
    if not domain:
        return None
    platform = get_platform_for_url(url, db)
    portal = db.query(Portal).filter(Portal.domain == domain).first()
    if not portal:
        portal = Portal(
            domain=domain,
            canonical_domain=domain,
            domain_status="active",
            portal_name=(platform or {}).get("name") or name or domain,
            portal_url=url,
            platform_key=(platform or {}).get("platform_key"),
            source_count=0,
        )
        db.add(portal)
        db.flush()
    else:
        if portal.domain_status in ("tracking", "ignored", "irrelevant"):
            portal.domain_status = "active" if ok else portal.domain_status
        portal.canonical_domain = domain
        if platform:
            portal.platform_key = platform["platform_key"]
    portal.source_count = (portal.source_count or 0) + 1
    return portal


def create_candidate(
    db: Session,
    run_id: int | None,
    source_type: str,
    title: str,
    source_url: str | None,
    snippet: str = "",
    sender: str = "",
    raw_content: str = "",
    gmail_message_id: str | None = None,
) -> DiscoveryCandidate:
    classification, confidence, reason = classify_candidate(title, snippet or raw_content, source_type, sender)
    domain = extract_domain(source_url)
    portal = get_or_create_portal(db, source_url, domain)
    cand = DiscoveryCandidate(
        run_id=run_id,
        source_type=source_type,
        title=title[:1000],
        source_url=source_url,
        domain=domain,
        portal_id=portal.id if portal else None,
        sender=sender or None,
        raw_snippet=(snippet or "")[:5000],
        raw_content=(raw_content or "")[:20000],
        classification=classification,
        classification_confidence=confidence,
        classification_reason=reason,
        extraction_status="pending",
        gmail_message_id=gmail_message_id,
    )
    db.add(cand)
    db.flush()
    return cand


def save_scholarship_from_dict(
    db: Session,
    raw: dict,
    query: str,
    why_saved: str,
    candidate_id: int | None = None,
) -> tuple[str, Scholarship | None]:
    """Returns action: saved|duplicate|rejected|skipped, scholarship."""
    name = (raw.get("name") or "").strip()
    if not name or len(name) < 5:
        return "skipped", None

    # Block listicle-style names even if classifier missed
    cls, _, reason = classify_candidate(name, raw.get("eligibility_notes") or "")
    if cls in ("scholarship_database_page", "scholarship_list_page", "spam", "loan", "irrelevant", "marketing"):
        return "rejected", None

    source = raw.get("source_url") or raw.get("application_url")
    from app.services.trusted_platforms import get_platform_for_url, should_create_scholarship

    ok, _block = should_create_scholarship(source, db)
    if not ok:
        return "rejected", None

    norm = normalize_url(source)
    dedupe = make_dedupe_key(name, source)
    trust, low_reason, skip = trust_heuristics(raw, source)
    if skip:
        return "rejected", None

    existing = None
    if dedupe:
        existing = db.query(Scholarship).filter(Scholarship.dedupe_key == dedupe).first()
    if not existing and norm:
        existing = db.query(Scholarship).filter(Scholarship.normalized_url == norm).first()

    if existing:
        if existing.user_edited:
            return "duplicate", existing
        merge_missing_fields(existing, raw)
        existing.why_saved = existing.why_saved or why_saved
        existing.updated_at = datetime.utcnow()
        return "duplicate", existing

    manual = bool(raw.get("manual_step_likely")) or raw.get("portal_login_required") == "yes"
    status = "maybe_eligible" if raw.get("international_allowed") == "unknown" else "found"
    if manual:
        status = "manual_step_needed"

    domain = extract_domain(source)
    portal = get_or_create_portal(db, source)
    platform = get_platform_for_url(source, db)

    sch = Scholarship(
        name=name,
        provider=raw.get("provider"),
        source_url=source,
        application_url=raw.get("application_url") or source,
        source_type=raw.get("source_type", "web"),
        award_amount=raw.get("award_amount"),
        deadline=parse_deadline(raw.get("deadline")),
        eligibility_notes=raw.get("eligibility_notes") or raw.get("notes"),
        required_documents=raw.get("required_documents"),
        essay_required=bool(raw.get("essay_required")) if raw.get("essay_required") is not None else False,
        essay_prompt=raw.get("essay_prompt"),
        citizenship_requirement=raw.get("citizenship_requirement"),
        major_requirement=raw.get("major_requirement"),
        education_level_requirement=raw.get("education_level_requirement"),
        gpa_requirement=raw.get("gpa_requirement"),
        international_allowed=raw.get("international_allowed") or "unknown",
        trust_score=trust,
        extraction_confidence=float(raw.get("extraction_confidence") or 50),
        portal_login_required=raw.get("portal_login_required") or "unknown",
        manual_step_likely=manual,
        low_trust_reason=low_reason,
        normalized_url=norm,
        dedupe_key=dedupe,
        discovered_at=datetime.utcnow(),
        search_query_used=query,
        status=status,
        next_action="Evaluate eligibility",
        effort_score=60.0 if raw.get("essay_required") else 40.0,
        classification=cls,
        why_saved=why_saved,
        portal_domain=domain,
        trusted_platform_key=(platform or {}).get("platform_key"),
        visibility_status="active",
        discovery_candidate_id=candidate_id,
        is_demo=False,
    )
    db.add(sch)
    db.flush()
    if portal:
        portal.opportunities_discovered = (portal.opportunities_discovered or 0) + 1
    return "saved", sch


async def process_candidate(db: Session, cand: DiscoveryCandidate, query: str) -> dict:
    """Classify, extract, save or reject a single candidate."""
    stats = {"saved": 0, "duplicate": 0, "rejected": 0, "source_page_only": 0}

    if cand.classification in ("spam", "loan", "irrelevant", "marketing"):
        cand.reject_reason = cand.classification_reason
        cand.extraction_status = "rejected"
        stats["rejected"] = 1
        return stats

    if should_save_as_scholarship(cand.classification):
        raw = {
            "name": cand.title,
            "source_url": cand.source_url,
            "application_url": cand.source_url,
            "eligibility_notes": cand.raw_snippet or cand.raw_content,
            "source_type": cand.source_type,
            "extraction_confidence": cand.classification_confidence * 100,
        }
        action, sch = save_scholarship_from_dict(
            db, raw, query, f"Classified as individual scholarship: {cand.classification_reason}", cand.id
        )
        if action == "saved":
            stats["saved"] += 1
        elif action == "duplicate":
            stats["duplicate"] += 1
        else:
            stats["rejected"] += 1
        if sch:
            cand.linked_scholarship_id = sch.id
            cand.extraction_status = "saved"
        elif action == "duplicate":
            cand.extraction_status = "duplicate"
            stats["duplicate"] = 1
        else:
            cand.reject_reason = "Failed trust or validation checks"
            cand.extraction_status = "rejected"
            stats["rejected"] = 1
        return stats

    if should_extract_from_page(cand.classification):
        # Try Gemini extraction from list/newsletter page
        fake_results = [{"title": cand.title, "url": cand.source_url, "content": cand.raw_content or cand.raw_snippet}]
        extracted = await structure_candidates_with_gemini(query, fake_results)
        saved_any = False
        for item in extracted:
            item["source_type"] = cand.source_type
            sub_cls, _, _ = classify_candidate(item.get("name", ""), item.get("eligibility_notes", ""))
            if sub_cls != "individual_scholarship":
                continue
            action, sch = save_scholarship_from_dict(
                db,
                item,
                query,
                f"Extracted from {cand.classification}: {cand.title[:80]}",
                cand.id,
            )
            if action == "saved":
                stats["saved"] += 1
                saved_any = True
            elif action == "duplicate":
                stats["duplicate"] += 1
        if saved_any:
            cand.extraction_status = "extracted"
        else:
            cand.extraction_status = "source_page_only"
            cand.reject_reason = "List/database page kept as lead only — no individual scholarships extracted"
            stats["source_page_only"] = 1
            # Optional: save portal lead scholarship with source_page_only status
            lead = Scholarship(
                name=f"[Source] {cand.title[:200]}",
                source_url=cand.source_url,
                source_type=cand.source_type,
                status="source_page_only",
                classification=cand.classification,
                why_saved=cand.classification_reason,
                portal_domain=cand.domain,
                discovery_candidate_id=cand.id,
                eligibility_notes="Lead page only — browse portal to find individual scholarships",
                is_demo=False,
            )
            db.add(lead)
            stats["source_page_only"] = 1
        return stats

    cand.reject_reason = cand.classification_reason or "Unknown classification"
    cand.extraction_status = "rejected"
    stats["rejected"] = 1
    return stats
