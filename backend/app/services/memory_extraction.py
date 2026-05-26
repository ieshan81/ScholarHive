"""AI memory extraction from document text."""
from __future__ import annotations

import hashlib
import json
import re

import httpx

from app.config import get_settings
from app.models.profile_graph import SENSITIVE_NODE_TYPES

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

NODE_TYPES = [
    "identity", "education", "university", "major", "international_status", "visa_status",
    "GPA", "academic_achievement", "project", "leadership", "volunteering", "work_experience",
    "family_background", "financial_need", "hardship", "personal_story", "career_goal",
    "mechanical_engineering_interest", "STEM_interest", "value", "award", "extracurricular",
    "essay_theme", "writing_style_sample",
]

CLUSTER_MAP = {
    "education": "Academic",
    "university": "Academic",
    "major": "Academic",
    "GPA": "Academic",
    "academic_achievement": "Academic",
    "project": "Projects",
    "leadership": "Leadership",
    "volunteering": "Leadership",
    "work_experience": "Leadership",
    "personal_story": "Personal Stories",
    "hardship": "Personal Stories",
    "family_background": "Personal Stories",
    "financial_need": "Financial Need",
    "career_goal": "Career Goals",
    "mechanical_engineering_interest": "Career Goals",
    "STEM_interest": "Career Goals",
    "identity": "Identity / Eligibility",
    "international_status": "Identity / Eligibility",
    "visa_status": "Identity / Eligibility",
    "writing_style_sample": "Writing Style",
    "value": "Values",
    "award": "Awards",
    "extracurricular": "Awards",
    "essay_theme": "Essay Themes",
}


def make_canonical_key(node_type: str, title: str, summary: str) -> str:
    raw = f"{node_type}|{title[:120]}|{(summary or '')[:200]}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def cluster_for_type(node_type: str) -> str:
    return CLUSTER_MAP.get(node_type, "Personal Stories")


def heuristic_extract(text: str, source_label: str) -> list[dict]:
    """Fallback when Gemini unavailable."""
    chunks = [c.strip() for c in re.split(r"\n{2,}", text) if len(c.strip()) > 60][:15]
    out = []
    for i, chunk in enumerate(chunks):
        lower = chunk.lower()
        ntype = "essay_theme"
        if any(w in lower for w in ("gpa", "grade point")):
            ntype = "GPA"
        elif "university" in lower or "college" in lower:
            ntype = "university"
        elif "project" in lower:
            ntype = "project"
        elif "leadership" in lower or "president" in lower:
            ntype = "leadership"
        elif "scholarship" in lower and "essay" in lower:
            ntype = "writing_style_sample"
        conf = 0.45
        out.append({
            "node_type": ntype,
            "title": f"{source_label} — excerpt {i + 1}",
            "summary": chunk[:500],
            "details": chunk[:2000],
            "source_excerpt": chunk[:800],
            "confidence": conf,
            "canonical_key": make_canonical_key(ntype, f"excerpt-{i}", chunk),
            "needs_review": True,
            "sensitive": ntype in SENSITIVE_NODE_TYPES,
        })
    return out


async def extract_memories_from_text(text: str, source_label: str = "document") -> list[dict]:
    settings = get_settings()
    if not settings.gemini_configured or len(text.strip()) < 80:
        return heuristic_extract(text, source_label)

    prompt = f"""Extract structured memory items from this personal document for scholarship essays.

RULES:
- Do NOT invent facts not present in the text.
- Each item must include a direct source_excerpt quote from the text.
- Assign node_type from: {", ".join(NODE_TYPES)}
- confidence 0.0-1.0
- sensitive=true for citizenship, visa, GPA, university, major, financial need, awards, dates affecting eligibility
- needs_review=true if uncertain or sensitive

Return JSON array only:
[{{"node_type":"","title":"","summary":"","details":"","source_excerpt":"","confidence":0.0,"canonical_key":"","sensitive":false,"needs_review":false}}]

Document ({source_label}):
{text[:12000]}
"""
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(GEMINI_URL, params={"key": settings.gemini_api_key}, json=payload)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            if isinstance(data, list):
                for item in data:
                    if not item.get("canonical_key"):
                        item["canonical_key"] = make_canonical_key(
                            item.get("node_type", "essay_theme"),
                            item.get("title", ""),
                            item.get("summary", ""),
                        )
                return data
    except Exception:
        pass
    return heuristic_extract(text, source_label)
