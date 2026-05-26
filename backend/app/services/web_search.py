"""Tavily web scholarship discovery — manual trigger only."""
from __future__ import annotations

import json
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.profile import Profile
from app.models.scholarship import Scholarship
from app.models.discovery import DiscoveryRun
from app.services.discovery_pipeline import create_candidate, process_candidate
from app.services.discovery_helpers import (
    normalize_url,
    make_dedupe_key,
    trust_heuristics,
    merge_missing_fields,
    parse_deadline,
    structure_candidates_with_gemini,
    structure_fallback,
)
from app.services.curated_sources import CURATED_SOURCE_HINTS
from app.services.trusted_platforms import trusted_only_enabled, trusted_search_queries

TAVILY_URL = "https://api.tavily.com/search"

DEFAULT_QUERIES = [
    "international student scholarships USA mechanical engineering",
    "mechanical engineering scholarships international students USA undergraduate",
    "undergraduate engineering scholarships international students USA",
    "scholarships for F1 visa students USA engineering",
    "private scholarships international students engineering USA",
    "STEM scholarships international students USA",
    "no essay scholarships international students USA",
    "mechanical engineering financial aid international students",
]

def build_queries_for_profile(profile: Profile | None, user_query: str | None) -> list[str]:
    if trusted_only_enabled():
        return trusted_search_queries(profile, user_query)
    if user_query and user_query.strip():
        return [user_query.strip()]
    queries = list(DEFAULT_QUERIES)
    if profile:
        if profile.major and "mechanical" in (profile.major or "").lower():
            queries.append("mechanical engineering merit scholarship international student USA 2025 2026")
        if profile.international_student:
            queries.append("international student private scholarship USA engineering undergraduate")
        if profile.personal_details and "pakistan" in profile.personal_details.lower():
            queries.append("scholarships for Pakistani international students USA engineering")
        if profile.university:
            queries.append(f"{profile.university} scholarship international student engineering")
    return queries[:6]


async def tavily_search(query: str, max_results: int = 8) -> list[dict]:
    settings = get_settings()
    if not settings.tavily_configured:
        return []
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_raw_content": False,
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(TAVILY_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])


def save_candidates(
    db: Session, candidates: list[dict], query: str
) -> dict:
    saved = duplicates = low_trust = 0
    for raw in candidates:
        name = (raw.get("name") or "").strip()
        if not name or len(name) < 5:
            continue
        source = raw.get("source_url") or raw.get("application_url")
        norm = normalize_url(source)
        dedupe = make_dedupe_key(name, source)
        trust, low_reason, skip = trust_heuristics(raw, source)
        if skip:
            low_trust += 1
            continue

        existing = None
        if dedupe:
            existing = db.query(Scholarship).filter(Scholarship.dedupe_key == dedupe).first()
        if not existing and norm:
            existing = db.query(Scholarship).filter(Scholarship.normalized_url == norm).first()

        essay_req = raw.get("essay_required")
        if essay_req is None:
            essay_bool = False
        else:
            essay_bool = bool(essay_req)

        if existing:
            if existing.user_edited:
                duplicates += 1
                continue
            merge_missing_fields(existing, raw)
            existing.updated_at = datetime.utcnow()
            duplicates += 1
            continue

        manual = bool(raw.get("manual_step_likely")) or raw.get("portal_login_required") == "yes"
        status = "maybe_eligible" if raw.get("international_allowed") == "unknown" else "found"
        if manual:
            status = "manual_step_needed"

        sch = Scholarship(
            name=name,
            provider=raw.get("provider"),
            source_url=source,
            application_url=raw.get("application_url") or source,
            source_type="web",
            award_amount=raw.get("award_amount"),
            deadline=parse_deadline(raw.get("deadline")),
            eligibility_notes=raw.get("eligibility_notes") or raw.get("notes"),
            required_documents=raw.get("required_documents"),
            essay_required=essay_bool,
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
            next_action="Evaluate eligibility" if not manual else "Complete manual portal steps",
            effort_score=60.0 if essay_bool else 40.0,
            is_demo=False,
        )
        db.add(sch)
        saved += 1
    db.commit()
    return {"saved": saved, "duplicates_skipped": duplicates, "low_trust_skipped": low_trust}


async def run_web_scholarship_search(db: Session, user_query: str | None = None) -> dict:
    settings = get_settings()
    if not settings.tavily_configured:
        return {
            "configured": False,
            "message": "Web Search not configured — add TAVILY_API_KEY",
        }

    profile = db.query(Profile).filter(Profile.id == 1).first()
    queries = build_queries_for_profile(profile, user_query)
    run = DiscoveryRun(source_type="web", query_or_label=queries[0], status="running")
    db.add(run)
    db.commit()

    all_results: list[dict] = []
    errors: list[str] = []
    total_saved = total_dup = total_rejected = total_candidates = 0
    try:
        for q in queries:
            try:
                hits = await tavily_search(q)
                query_stats = {"saved": 0, "duplicate": 0, "rejected": 0, "source_page_only": 0, "hits": len(hits)}
                for hit in hits:
                    title = (hit.get("title") or "").strip()
                    if not title:
                        continue
                    cand = create_candidate(
                        db,
                        run.id,
                        "web",
                        title,
                        hit.get("url"),
                        snippet=hit.get("content") or "",
                        raw_content=hit.get("content") or "",
                    )
                    total_candidates += 1
                    ps = await process_candidate(db, cand, q)
                    for k, v in ps.items():
                        query_stats[k] = query_stats.get(k, 0) + v
                db.commit()
                all_results.append({"query": q, **query_stats})
                total_saved += query_stats.get("saved", 0)
                total_dup += query_stats.get("duplicate", 0)
                total_rejected += query_stats.get("rejected", 0) + query_stats.get("source_page_only", 0)
            except Exception as e:
                errors.append(f"{q}: {e}")

        run.status = "completed" if not errors else "completed_with_errors"
        run.total_candidates = total_candidates
        run.opportunities_saved = total_saved
        run.duplicates_skipped = total_dup
        run.rejected_count = total_rejected
        run.errors = "\n".join(errors) if errors else None
        run.log_summary = json.dumps(all_results)
        run.finished_at = datetime.utcnow()
        db.commit()

        return {
            "configured": True,
            "message": f"Discovery complete — {total_saved} scholarships saved, {total_rejected} rejected/filtered",
            "run_id": run.id,
            "queries_run": queries,
            "total_candidates": total_candidates,
            "saved": total_saved,
            "duplicates_skipped": total_dup,
            "rejected_count": total_rejected,
            "errors": errors,
            "details": all_results,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }
    except Exception as e:
        run.status = "failed"
        run.errors = str(e)
        run.finished_at = datetime.utcnow()
        db.commit()
        return {"configured": True, "message": f"Web search failed: {e}", "errors": [str(e)]}


def web_search_status(db: Session) -> dict:
    settings = get_settings()
    last = db.query(DiscoveryRun).filter(DiscoveryRun.source_type == "web").order_by(
        DiscoveryRun.started_at.desc()
    ).first()
    trusted = trusted_only_enabled()
    return {
        "configured": settings.tavily_configured,
        "gemini_recommended": settings.gemini_configured,
        "trusted_only_mode": trusted,
        "trusted_platform_search": trusted,
        "platforms_included": ["Scholarship America", "Kaleidoscope", "Fastweb"] if trusted else [],
        "broad_search_available": not trusted,
        "status": "configured" if settings.tavily_configured else "not_configured",
        "message": (
            "Trusted-only platform search active (Scholarship America, Kaleidoscope, Fastweb)."
            if trusted
            else ("Tavily ready" if settings.tavily_configured else "Add TAVILY_API_KEY for web scholarship search")
        ),
        "last_run": {
            "id": last.id,
            "search_query": last.query_or_label,
            "status": last.status,
            "total_candidates": last.total_candidates,
            "saved_count": last.opportunities_saved,
            "duplicates_skipped": last.duplicates_skipped,
            "rejected_count": last.rejected_count,
            "started_at": last.started_at.isoformat() if last.started_at else None,
            "finished_at": last.finished_at.isoformat() if last and last.finished_at else None,
            "errors": last.errors,
        } if last else None,
        "default_queries": DEFAULT_QUERIES,
        "curated_hints": CURATED_SOURCE_HINTS[:5],
    }
