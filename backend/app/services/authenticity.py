"""Personal Voice Review — truthful, specific writing; not AI-detector evasion."""

GENERIC_PHRASES = [
    "passionate about", "ever since i was young", "make a difference",
    "unique perspective", "dedicated individual", "further my education",
    "pursue my dreams", "humbled and honored", "in today's world",
    "throughout my journey", "i believe that", "transformative experience",
    "leverage my skills", "dynamic environment", "synergy", "holistic",
]

ROBOTIC_PATTERNS = [
    "furthermore", "moreover", "in conclusion", "it is important to note",
    "this experience taught me", "additionally", "in addition",
]

CLICHE_PHRASES = [
    "blessed", "grateful for this opportunity", "dream come true",
    "change the world", "make an impact", "giving back to the community",
]

REWRITE_MODES = {
    "more_specific": "Add concrete details (course, project, date) from profile/stories only.",
    "more_natural": "Use simpler, direct sentences; reduce corporate tone.",
    "add_story_evidence": "Weave in one verified Story Bank entry; do not invent events.",
    "reduce_generic": "Remove clichés and generic AI phrases.",
    "tighten_word_count": "Shorten while keeping facts; remove filler.",
    "align_prompt": "Ensure every part of the essay prompt is answered.",
    "keep_voice": "Preserve the student's tone; only clarify awkward phrasing.",
}


def _profile_keywords(profile_text: str) -> set[str]:
    words = set()
    for w in profile_text.lower().split():
        if len(w) > 5:
            words.add(w.strip(".,;:"))
    return words


def review_essay(
    text: str | None,
    prompt: str | None = None,
    profile_text: str = "",
    stories_text: str = "",
) -> dict:
    if not text or not text.strip():
        return {
            "authenticity_score": 0.0,
            "prompt_alignment_score": 0.0,
            "generic_language_flags": ["Essay is empty"],
            "unsupported_claims": [],
            "missing_evidence": ["No essay content to review"],
            "review_suggestions": ["Add a draft before running Personal Voice Review"],
            "rewrite_modes_available": list(REWRITE_MODES.keys()),
            "message": "No content to review",
        }

    lower = text.lower()
    generic_flags: list[str] = []
    suggestions: list[str] = []
    profile_kw = _profile_keywords(profile_text + " " + stories_text)

    for phrase in GENERIC_PHRASES + CLICHE_PHRASES:
        if phrase in lower:
            generic_flags.append(f"Generic or cliché wording: \"{phrase}\"")

    for phrase in ROBOTIC_PATTERNS:
        if phrase in lower:
            generic_flags.append(f"Robotic transition: \"{phrase}\"")

    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if len(sentences) >= 4:
        starters = [s.split()[0].lower() if s.split() else "" for s in sentences[:12]]
        if starters and len(set(starters)) < len(starters) * 0.5:
            generic_flags.append("Repetitive sentence openings")

    vague = ["many achievements", "various experiences", "several projects", "numerous awards", "always excelled"]
    unsupported = [v for v in vague if v in lower]

    missing_evidence: list[str] = []
    if "leadership" in lower and not any(w in lower for w in ("fsae", "team", "led", "president", "captain")):
        missing_evidence.append("Leadership claim needs a specific verified example from Story Bank")
    if "financial" in lower and "story bank" not in lower and stories_text and "financial" not in stories_text.lower():
        missing_evidence.append("Financial hardship mentioned — add a verified financial story or remove claim")
    if prompt:
        prompt_words = [w for w in prompt.lower().split() if len(w) > 5][:8]
        if not any(w in lower for w in prompt_words):
            missing_evidence.append("Essay may not address the prompt — compare line by line")

    # Claims not grounded in profile/stories
    claim_words = ["award", "published", "patent", "internship at", "dean's list"]
    for cw in claim_words:
        if cw in lower and cw.replace(" ", "") not in profile_text.lower().replace(" ", ""):
            if not any(cw in stories_text.lower() for _ in [1]):
                unsupported.append(f"Verify claim involving '{cw}' against Profile Vault")

    if text[:100].lower().count("i ") < 1:
        suggestions.append("Weak opening — start with a specific moment, not a general statement")
    if len(text.split()) < 80:
        suggestions.append("Draft is short — expand with verified details only")
    if lower.count("engineering") < 1 and "mechanical" in profile_text.lower():
        suggestions.append("Connect essay to mechanical engineering goals using real projects")

    suggestions.extend([
        "Personal Voice Review improves honesty and specificity — not AI-detector evasion",
        "Replace one vague sentence with a dated fact from Profile Vault or Story Bank",
        "End with a concrete next step tied to your engineering path",
    ])

    auth_score = max(0, 100 - len(generic_flags) * 7 - len(unsupported) * 12 - len(missing_evidence) * 8)
    align_score = 55.0
    if prompt:
        overlap = sum(1 for w in prompt.lower().split() if len(w) > 4 and w in lower)
        align_score += min(35, overlap * 5)

    return {
        "authenticity_score": round(min(100, auth_score), 1),
        "prompt_alignment_score": round(min(100, align_score), 1),
        "generic_language_flags": generic_flags[:15],
        "unsupported_claims": unsupported[:10],
        "missing_evidence": missing_evidence[:10],
        "review_suggestions": suggestions[:12],
        "rewrite_modes_available": list(REWRITE_MODES.keys()),
        "message": "Personal Voice Review complete — improve specificity without inventing facts",
    }


async def rewrite_essay_section(
    text: str,
    mode: str,
    prompt: str | None,
    profile_text: str,
    stories_text: str,
) -> dict:
    if mode not in REWRITE_MODES:
        return {"success": False, "message": f"Unknown mode. Choose: {', '.join(REWRITE_MODES)}"}

    instruction = REWRITE_MODES[mode]
    from app.config import get_settings
    settings = get_settings()

    if not settings.gemini_configured:
        review = review_essay(text, prompt, profile_text, stories_text)
        return {
            "success": True,
            "configured": False,
            "message": "Gemini not configured — suggestions only (no auto-rewrite)",
            "suggestions": review["review_suggestions"],
            "revised_text": None,
        }

    gemini_prompt = f"""Personal Voice Review rewrite ({mode}).
{instruction}

RULES: Do NOT invent facts. Use ONLY profile and stories below. If missing info, insert [MISSING: what is needed].
Do NOT optimize for AI detectors. Improve truthful, personal, scholarship-quality writing.

Essay prompt: {prompt or 'N/A'}

Profile:
{profile_text or 'None'}

Stories:
{stories_text or 'None'}

Essay:
{text}

Return JSON: {{"revised_text":"...","changes_summary":["..."],"missing_info":["..."]}}
"""
    try:
        import json
        import httpx

        payload = {
            "contents": [{"parts": [{"text": gemini_prompt}]}],
            "generationConfig": {"temperature": 0.35, "maxOutputTokens": 2048},
        }
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            return {
                "success": True,
                "configured": True,
                "message": f"Rewrite mode: {mode}",
                "revised_text": parsed.get("revised_text"),
                "changes_summary": parsed.get("changes_summary", []),
                "missing_info": parsed.get("missing_info", []),
            }
    except Exception as e:
        return {"success": False, "message": str(e), "revised_text": None}
