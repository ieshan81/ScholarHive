"""Gemini essay draft engine — only calls API when configured."""
import json
import httpx
from app.config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _build_prompt(
    scholarship_name: str,
    essay_prompt: str,
    profile_text: str,
    memory_text: str,
    writing_style: str,
) -> str:
    return f"""You are helping an international mechanical engineering student draft a scholarship essay.
RULES (mandatory):
- Do NOT invent facts, awards, dates, or experiences not in the Memory Vault excerpts below.
- Cite only details supported by the provided memory excerpts.
- If information is missing, list it in missing_topics — do not fabricate.
- Write in first person, specific and personal, avoid generic AI phrases.
- Match the student's natural voice using writing style samples when provided.
- Answer the essay prompt directly.

Scholarship: {scholarship_name}
Prompt: {essay_prompt}

Basic profile:
{profile_text or "No profile data"}

Memory Vault (approved facts & stories — use these):
{memory_text or "No memory vault data — ask user to upload essays/resume in Memory Vault"}

Writing style samples (match tone, not content):
{writing_style or "No writing style samples yet"}

Return JSON only:
{{"draft_text": "...", "missing_topics": ["..."], "unsupported_risks": ["..."], "memories_used": ["title or excerpt reference"]}}
"""


async def generate_essay_draft(
    scholarship_name: str,
    essay_prompt: str,
    profile_text: str,
    memory_text: str,
    writing_style: str = "",
) -> dict:
    settings = get_settings()
    if not settings.gemini_configured:
        return {
            "configured": False,
            "message": "Gemini not configured — add GEMINI_API_KEY to environment",
            "draft_text": None,
            "missing_topics": ["Gemini API key required for AI drafts"],
            "memories_used": [],
        }

    prompt = _build_prompt(scholarship_name, essay_prompt, profile_text, memory_text, writing_style)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                GEMINI_URL,
                params={"key": settings.gemini_api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            parsed = json.loads(text.strip())
            return {
                "configured": True,
                "message": "Draft generated from Memory Vault",
                "draft_text": parsed.get("draft_text", ""),
                "missing_topics": parsed.get("missing_topics", []),
                "unsupported_risks": parsed.get("unsupported_risks", []),
                "memories_used": parsed.get("memories_used", []),
            }
    except Exception as e:
        return {
            "configured": True,
            "message": f"Gemini request failed: {e}",
            "draft_text": None,
            "missing_topics": ["Generation failed — use manual draft or retry"],
            "memories_used": [],
        }
