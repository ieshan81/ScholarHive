"""Classify discovery candidates before saving scholarships."""
import re
from urllib.parse import urlparse

LIST_PAGE_PATTERNS = [
    r"\b\d{2,4}\+?\s*(mechanical engineering\s+)?scholarships\b",
    r"\b\d{2,4}\s+scholarships\s+available\b",
    r"\btop\s+\d{1,4}\s+scholarships\b",
    r"\blist\s+of\s+scholarships\b",
    r"\bscholarship\s+database\b",
    r"\bscholarship\s+search\b",
    r"\bfind\s+scholarships\b",
    r"\bbrowse\s+scholarships\b",
    r"\d{2,4}\+?\s+.*scholarships\s+in\s+(the\s+)?(united states|usa)\b",
    r"\bavailable\s+in\s+the\s+usa\b",
    r"\bscholarships\s+for\s+.*students\s+in\s+.*\d{4}\b",
]

LOAN_MARKETING = [
    "student loan", "refinance", "personal loan", "credit card", "pre-approved",
    "loan forgiveness scam", "borrow money", "interest rate apr",
]

IRRELEVANT_SUBJECT = [
    "app demo", "real business", "newsletter", "unsubscribe", "sale ends",
    "black friday", "job alert", "linkedin", "password reset", "verify your account",
]

SPAM_MARKERS = ["win money", "guaranteed scholarship", "click here to claim", "you've been selected"]


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url if "://" in url else f"https://{url}").netloc.lower().replace("www.", "")
    except Exception:
        return None


def classify_candidate(title: str, snippet: str = "", source_type: str = "web", sender: str = "") -> tuple[str, float, str]:
    """
    Returns (classification, confidence, reason).
    """
    text = f"{title} {snippet} {sender}".lower()
    title_lower = (title or "").lower()

    if any(m in text for m in SPAM_MARKERS):
        return "spam", 0.9, "Spam-like promotional language"

    if any(m in text for m in LOAN_MARKETING):
        return "loan", 0.85, "Appears to be loan/credit marketing"

    for pat in IRRELEVANT_SUBJECT:
        if pat in title_lower or pat in text:
            return "irrelevant", 0.88, f"Irrelevant content signal: {pat}"

    if source_type == "gmail":
        if "scholarship" not in text and "financial aid" not in text and "fellowship" not in text and "grant" not in text:
            if "award" not in text or "demo" in text or "business" in text:
                return "irrelevant", 0.8, "Gmail message lacks scholarship signals"

    for pat in LIST_PAGE_PATTERNS:
        if re.search(pat, title_lower, re.I):
            return "scholarship_database_page", 0.92, "Title matches scholarship list/database page pattern"

    if any(w in title_lower for w in ("database", "search scholarships", "find scholarships", "browse all")):
        return "scholarship_database_page", 0.8, "Database/search listing page"

    if "newsletter" in title_lower or "weekly digest" in text:
        return "scholarship_newsletter", 0.75, "Newsletter — extract individual links if present"

    if source_type == "gmail" and any(w in text for w in ("application received", "status update", "submitted")):
        return "application_update", 0.7, "Application status update"

    if "financial aid" in text and "university" in text and "scholarship" not in title_lower:
        return "university_financial_aid_page", 0.65, "University financial aid page"

    # Individual scholarship signals
    if re.search(r"\$[\d,]+", text) or "deadline" in text or "apply now" in text:
        if not re.search(r"\b\d{2,4}\+?\s+scholarships\b", title_lower):
            return "individual_scholarship", 0.72, "Contains award/deadline/application signals"

    if len(title_lower.split()) <= 12 and "scholarship" in title_lower and not re.search(r"\b\d{2,4}\b", title_lower):
        return "individual_scholarship", 0.6, "Single scholarship-style title"

    return "unknown", 0.4, "Could not confidently classify — needs review"


def should_save_as_scholarship(classification: str) -> bool:
    return classification == "individual_scholarship"


def should_extract_from_page(classification: str) -> bool:
    return classification in (
        "scholarship_list_page",
        "scholarship_database_page",
        "scholarship_newsletter",
        "university_financial_aid_page",
        "unknown",
    )
