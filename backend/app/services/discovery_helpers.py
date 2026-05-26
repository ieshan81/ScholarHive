"""Shared discovery/scholarship save helpers (no pipeline imports)."""
from __future__ import annotations

import json
from datetime import date
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from app.config import get_settings
from app.models.scholarship import Scholarship
from app.services.curated_sources import CURATED_DOMAINS_TRUSTED, SUSPICIOUS_DOMAIN_HINTS

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


def trust_heuristics(candidate: dict, source_url: str | None) -> tuple[float, str | None, bool]:
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


def parse_deadline(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    s = str(val)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def merge_missing_fields(existing: Scholarship, data: dict) -> None:
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
        existing.deadline = parse_deadline(data.get("deadline"))
    if data.get("extraction_confidence") and not existing.extraction_confidence:
        existing.extraction_confidence = float(data.get("extraction_confidence", 0))


def structure_fallback(results: list[dict]) -> list[dict]:
    out = []
    for r in results:
        title = (r.get("title") or "").strip()
        if not title or (
            "scholarship" not in title.lower()
            and "grant" not in title.lower()
            and "fellowship" not in title.lower()
        ):
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


async def structure_candidates_with_gemini(query: str, search_results: list[dict]) -> list[dict]:
    settings = get_settings()
    if not settings.gemini_configured or not search_results:
        return structure_fallback(search_results)

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
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        async with httpx.AsyncClient(timeout=90.0) as client:
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
    return structure_fallback(search_results)
