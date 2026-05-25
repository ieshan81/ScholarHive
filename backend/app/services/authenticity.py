"""Personal Voice / Authenticity Review — honest writing quality, not AI-detector evasion."""

GENERIC_PHRASES = [
    "passionate about",
    "ever since i was young",
    "make a difference",
    "unique perspective",
    "dedicated individual",
    "further my education",
    "pursue my dreams",
    "humbled and honored",
    "in today's world",
    "throughout my journey",
    "i believe that",
    "not only... but also",
]

ROBOTIC_PATTERNS = [
    "furthermore",
    "moreover",
    "in conclusion",
    "it is important to note",
    "this experience taught me",
]


def review_essay(text: str | None, prompt: str | None = None) -> dict:
    if not text or not text.strip():
        return {
            "authenticity_score": 0.0,
            "prompt_alignment_score": 0.0,
            "generic_language_flags": ["Essay is empty"],
            "unsupported_claims": [],
            "missing_evidence": ["No essay content to review"],
            "review_suggestions": ["Add a draft before running Authenticity Review"],
            "message": "No content to review",
        }

    lower = text.lower()
    generic_flags: list[str] = []
    suggestions: list[str] = []

    for phrase in GENERIC_PHRASES:
        if phrase in lower:
            generic_flags.append(f"Generic phrase detected: \"{phrase}\"")

    for phrase in ROBOTIC_PATTERNS:
        if phrase in lower:
            generic_flags.append(f"Possibly over-formal: \"{phrase}\"")

    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if sentences and len(set(sentences)) < len(sentences) * 0.7:
        generic_flags.append("Repetitive sentence structure")

    vague = ["many achievements", "various experiences", "several projects", "numerous awards"]
    unsupported = [v for v in vague if v in lower]

    missing_evidence: list[str] = []
    if "leadership" in lower and "specific" not in lower and "when" not in lower:
        missing_evidence.append("Leadership mentioned — add a specific example with date/context")
    if "financial" in lower and "because" not in lower and "family" not in lower:
        missing_evidence.append("Financial theme — tie to a verified Story Bank entry")
    if prompt and prompt.lower()[:40] not in lower and len(prompt) > 20:
        missing_evidence.append("Prompt may not be fully addressed — compare each question to your draft")

    if text[:80].count("I") < 1:
        suggestions.append("Strengthen opening with a specific personal moment")
    if len(text.split()) < 100:
        suggestions.append("Draft may be short — expand with concrete details from Story Bank")

    suggestions.extend([
        "Replace vague claims with one verifiable detail (course, project, date)",
        "End with a forward-looking sentence tied to mechanical engineering goals",
        "Cross-check every claim against Profile Vault and verified stories",
    ])

    auth_score = max(0, 100 - len(generic_flags) * 8 - len(unsupported) * 10 - len(missing_evidence) * 7)
    align_score = 70.0 if prompt else 60.0
    if prompt and any(kw in lower for kw in prompt.lower().split()[:5]):
        align_score += 15

    return {
        "authenticity_score": round(min(100, auth_score), 1),
        "prompt_alignment_score": round(min(100, align_score), 1),
        "generic_language_flags": generic_flags[:12],
        "unsupported_claims": unsupported,
        "missing_evidence": missing_evidence,
        "review_suggestions": suggestions[:10],
        "message": "Personal Voice Review complete — improve specificity without inventing facts",
    }
