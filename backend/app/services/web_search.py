"""Tavily web scholarship discovery — manual trigger only."""
from __future__ import annotations

import json
import re
from datetime import datetime, date
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.profile import Profile
from app.models.scholarship import Scholarship
from app.models.web_search_run import WebSearchRun
from app.services.curated_sources import CURATED_SOURCE_HINTS, CURATED_DOMAINS_TRUSTED, SUSPICIOUS_DOMAIN_HINTS
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

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def normalize_url(url: str | None) -> str | None:
    if not url or not url.strip():
        return None
    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme:
            parsed = urlparse("https://" + url.strip())
        qs = parse_qs(parsed.query)
        clean = {k: v for k, v in qs.items() if k.lower() not in TRACKING_PARAMS}
        new_query = urlencode(clean, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", new_query, ""))
    except Exception:
        return url.strip().lower()


def make_dedupe_key(name: str, url: str | None) -> str:
    norm = normalize_url(url) or ""
    return f"{name.strip().lower()[:200]}|{norm}"


def build_queries_for_profile(profile: Profile | None, user_query: str | None) -> list[str]:
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


def _trust_heuristics(candidate: dict, source_url: str | None) -> tuple[float, str | None, bool]:
    """Returns trust_score, low_trust_reason, skip."""
    score = 70.0
    reasons: list[str] = []
    url = (source_url or "").lower()
    name = (candidate.get("name") or "").lower()
    notes = (candidate.get("eligibility_notes") or "").lower()

    if not source_url:
        score -= 25
        reasons.append("No source URL")
    if not candidate.get("provider"):
        score -= 10
        reasons.append("No official provider identified")
    if not candidate.get("deadline") and not candidate.get("award_amount"):
        score -= 15
        reasons.append("Missing deadline and award amount")
    if any(s in url or s in name or s in notes for s in SUSPICIOUS_DOMAIN_HINTS):
        return 10.0, "Suspicious or spam-like signals", True
    if "pay" in notes and "fee" in notes:
        return 5.0, "May require payment to apply", True
    if url and not any(d in url for d in CURATED_DOMAINS_TRUSTED) and "scholarship" not in url:
        score -= 10
    if any(d in url for d in CURATED_DOMAINS_TRUSTED):
        score += 15
    if candidate.get("portal_login_required") == "yes" or candidate.get("manual_step_likely"):
        score -= 5
        reasons.append("Portal/manual steps likely — review carefully")

    low = "; ".join(reasons) if reasons and score < 50 else None
    return max(0, min(100, score)), low, score < 25


async def structure_candidates_with_gemini(
    query: str, search_results: list[dict]
) -> list[dict]:
    settings = get_settings()
    if not settings.gemini_configured or not search_results:
        return _structure_fallback(search_results)

    snippets = []
    for r in search_results[:12]:
        snippets.append(
            f"Title: {r.get('title','')}\nURL: {r.get('url','')}\nContent: {(r.get('content') or '')[:800]}"
        )
    prompt = f"""Extract scholarship opportunities from these web search results for query: {query}

RULES:
- Only include real scholarship/grant/fellowship opportunities.
- Do NOT invent scholarships not supported by the snippets.
- If unclear, set fields to null or "unknown".
- Mark portal_login_required yes if login/account needed.
- Mark manual_step_likely true if portal, CAPTCHA, signature, or certification likely.

Return JSON array only:
[{{"name":"","provider":"","source_url":"","application_url":"","award_amount":"","deadline":"YYYY-MM-DD or null",
"eligibility_notes":"","citizenship_requirement":"","international_allowed":"yes|no|unknown",
"major_requirement":"","education_level_requirement":"","gpa_requirement":"","required_documents":"",
"essay_required":true/false/null,"essay_prompt":"","portal_login_required":"yes|no|unknown",
"manual_step_likely":true/false,"extraction_confidence":0-100,"notes":""}}]

Search results:
{chr(10).join(snippets)}
"""
    try:
        import httpx as hx

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        async with hx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return _structure_fallback(search_results)


def _structure_fallback(results: list[dict]) -> list[dict]:
    out = []
    for r in results:
        title = (r.get("title") or "").strip()
        if not title or "scholarship" not in title.lower() and "grant" not in title.lower() and "fellowship" not in title.lower():
            continue
        out.append({
            "name": title[:500],
            "provider": None,
            "source_url": r.get("url"),
            "application_url": r.get("url"),
            "award_amount": None,
            "deadline": None,
            "eligibility_notes": (r.get("content") or "")[:1000],
            "international_allowed": "unknown",
            "essay_required": None,
            "portal_login_required": "unknown",
            "manual_step_likely": False,
            "extraction_confidence": 35.0,
            "notes": "Structured from search snippet only — verify on official site",
        })
    return out


def _parse_deadline(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    s = str(val)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _merge_missing_fields(existing: Scholarship, data: dict) -> None:
    """Fill only empty fields — never overwrite user-edited records."""
    if existing.user_edited:
        return
    mapping = {
        "provider": "provider",
        "application_url": "application_url",
        "award_amount": "award_amount",
        "eligibility_notes": "eligibility_notes",
        "required_documents": "required_documents",
        "essay_prompt": "essay_prompt",
        "citizenship_requirement": "citizenship_requirement",
        "major_requirement": "major_requirement",
        "education_level_requirement": "education_level_requirement",
        "gpa_requirement": "gpa_requirement",
        "international_allowed": "international_allowed",
        "portal_login_required": "portal_login_required",
    }
    for attr, key in mapping.items():
        if getattr(existing, attr) in (None, "", "unknown") and data.get(key):
            setattr(existing, attr, data.get(key))
    if not existing.deadline and data.get("deadline"):
        existing.deadline = _parse_deadline(data.get("deadline"))
    if data.get("extraction_confidence") and not existing.extraction_confidence:
        existing.extraction_confidence = float(data.get("extraction_confidence", 0))


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
        trust, low_reason, skip = _trust_heuristics(raw, source)
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
            _merge_missing_fields(existing, raw)
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
            deadline=_parse_deadline(raw.get("deadline")),
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
    run = WebSearchRun(search_query=queries[0], status="running")
    db.add(run)
    db.commit()

    all_results: list[dict] = []
    errors: list[str] = []
    try:
        for q in queries:
            try:
                hits = await tavily_search(q)
                structured = await structure_candidates_with_gemini(q, hits)
                stats = save_candidates(db, structured, q)
                all_results.append({"query": q, "hits": len(hits), **stats})
            except Exception as e:
                errors.append(f"{q}: {e}")

        total_saved = sum(r.get("saved", 0) for r in all_results)
        total_dup = sum(r.get("duplicates_skipped", 0) for r in all_results)
        total_low = sum(r.get("low_trust_skipped", 0) for r in all_results)
        total_found = sum(r.get("hits", 0) for r in all_results)

        run.status = "completed" if not errors else "completed_with_errors"
        run.results_found = total_found
        run.saved_count = total_saved
        run.duplicates_skipped = total_dup
        run.low_trust_skipped = total_low
        run.errors = "\n".join(errors) if errors else None
        run.log_summary = json.dumps(all_results)
        run.finished_at = datetime.utcnow()
        db.commit()

        return {
            "configured": True,
            "message": f"Web search complete — {total_saved} new opportunities saved",
            "run_id": run.id,
            "queries_run": queries,
            "results_found": total_found,
            "saved": total_saved,
            "duplicates_skipped": total_dup,
            "low_trust_skipped": total_low,
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
    last = db.query(WebSearchRun).order_by(WebSearchRun.started_at.desc()).first()
    return {
        "configured": settings.tavily_configured,
        "gemini_recommended": settings.gemini_configured,
        "status": "configured" if settings.tavily_configured else "not_configured",
        "message": "Tavily ready" if settings.tavily_configured else "Add TAVILY_API_KEY for web scholarship search",
        "last_run": {
            "id": last.id,
            "search_query": last.search_query,
            "status": last.status,
            "results_found": last.results_found,
            "saved_count": last.saved_count,
            "duplicates_skipped": last.duplicates_skipped,
            "low_trust_skipped": last.low_trust_skipped,
            "started_at": last.started_at.isoformat() if last.started_at else None,
            "finished_at": last.finished_at.isoformat() if last and last.finished_at else None,
            "errors": last.errors,
        } if last else None,
        "default_queries": DEFAULT_QUERIES,
        "curated_hints": CURATED_SOURCE_HINTS[:5],
    }
