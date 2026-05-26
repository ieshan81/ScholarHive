"""Portal link quality gate — accept only real individual scholarship opportunities."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from app.services.discovery_helpers import normalize_url
from app.services.portal_domain import is_blocked_domain, quick_canonical_domain, unwrap_google_redirect

SAVEABLE_CLASSIFICATIONS = frozenset({"individual_opportunity", "application_page"})
MIN_SAVE_CONFIDENCE = 65

APP_STORE_DOMAINS = frozenset({
    "itunes.apple.com",
    "apps.apple.com",
    "play.google.com",
    "appstore.com",
})

SOCIAL_DOMAINS = frozenset({
    "linkedin.com",
    "www.linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
})

TRACKING_DOMAIN_FRAGMENTS = (
    "ablink.",
    "sendgrid",
    "list-manage.com",
    "mailchimp",
    "spmailtechno",
    "go.anything.com",
    "click.",
    "tracking",
    "unsubscribe",
    "email preference",
    "safelinks",
    "urldefense",
)

DONATE_PATH_FRAGMENTS = (
    "/donate",
    "/donation",
    "/give",
    "/checkout",
    "/payment",
    "paypal",
    "stripe",
)

CATEGORY_TITLE_PATTERNS = [
    re.compile(r"^scholarships?\s+for\s+", re.I),
    re.compile(r"^scholarships?\s+by\s+", re.I),
    re.compile(r"^browse\s+scholarships?", re.I),
    re.compile(r"^search\s+scholarships?", re.I),
    re.compile(r"^scholarship\s+directory", re.I),
    re.compile(r"^featured\s+scholarships?", re.I),
    re.compile(r"^college\s+scholarships?$", re.I),
    re.compile(r"^scholarship\s+categor", re.I),
    re.compile(r"^financial\s+aid\s+resources?", re.I),
    re.compile(r"^(blog|news|articles?)\b", re.I),
    re.compile(r"^fastweb\s+college\s+scholarships?\s+app", re.I),
    re.compile(r"^download\s+(the\s+)?app", re.I),
    re.compile(r"^scholarships?\s+for\s+(african|hispanic|bilingual|veteran|women|men|lgbt)", re.I),
]

GENERIC_NAV_PATTERNS = re.compile(
    r"\b(browse|directory|categories?|featured scholarships|all scholarships|"
    r"scholarship search|find scholarships|view all|sign up free)\b",
    re.I,
)

INDIVIDUAL_POSITIVE = re.compile(
    r"\b(program|foundation|scholars?|fellowship|grant|award|prize)\b",
    re.I,
)
SPECIFIC_PROGRAM = re.compile(
    r"\b(the\s+)?[\w\s]{3,60}\s+(scholarship|scholars program|fellowship|grant)\b",
    re.I,
)


def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def canonicalize_opportunity_url(url: str | None) -> str | None:
    if not url or not str(url).strip():
        return None
    u = unwrap_google_redirect(normalize_url(url.strip()) or url.strip())
    return u


def classify_portal_link(
    text: str,
    href: str,
    context: str = "",
    final_url: str | None = None,
    portal_domain: str | None = None,
) -> dict:
    """Classify a portal link for opportunity saving."""
    raw_href = (href or "").strip()
    link_text = (text or "").strip()
    ctx = (context or "")[:5000]
    combined = f"{link_text} {raw_href} {ctx}".lower()

    canonical_url = canonicalize_opportunity_url(final_url or raw_href)
    canonical_domain = quick_canonical_domain(canonical_url or raw_href) or _host(canonical_url or raw_href)

    base = {
        "canonical_url": canonical_url,
        "canonical_domain": canonical_domain,
        "classification": "unknown",
        "save": False,
        "confidence": 0,
        "reason": "Unclassified link",
    }

    if not raw_href or raw_href.startswith("javascript:"):
        return {**base, "classification": "irrelevant", "reason": "Empty or invalid URL"}

    host = _host(canonical_url or raw_href)

    # App stores
    if host in APP_STORE_DOMAINS or "itunes.apple.com" in combined or "play.google.com" in combined:
        if re.search(r"\bapp\b|itunes|google play|download", combined, re.I):
            return {
                **base,
                "classification": "app_store",
                "confidence": 95,
                "reason": "App Store / mobile app promotion link",
            }

    # Social
    if host in SOCIAL_DOMAINS or any(s in host for s in ("linkedin.com", "facebook.com", "instagram.com")):
        return {
            **base,
            "classification": "social",
            "confidence": 92,
            "reason": "Social media link, not a scholarship opportunity",
        }

    # Tracking / marketing
    if is_blocked_domain(host) or is_blocked_domain(canonical_domain):
        return {
            **base,
            "classification": "tracking_link",
            "confidence": 90,
            "reason": "Tracking or blocked email/marketing domain",
        }
    if any(frag in host for frag in TRACKING_DOMAIN_FRAGMENTS):
        return {
            **base,
            "classification": "tracking_link",
            "confidence": 88,
            "reason": "Email tracking or marketing redirect domain",
        }
    if "google.com/url" in combined or "/url?" in raw_href.lower():
        if not canonical_domain or is_blocked_domain(canonical_domain):
            return {
                **base,
                "classification": "tracking_link",
                "confidence": 85,
                "reason": "Unresolved Google redirect wrapper",
            }

    # Donation / payment
    path_lower = (urlparse(canonical_url or raw_href).path or "").lower()
    if any(p in path_lower for p in DONATE_PATH_FRAGMENTS) or re.search(
        r"\b(donate|donation|give now|checkout|payment required)\b", combined, re.I
    ):
        return {
            **base,
            "classification": "donation",
            "confidence": 90,
            "reason": "Donation or payment page, not a scholarship",
        }

    # Category / listing navigation
    for pat in CATEGORY_TITLE_PATTERNS:
        if pat.search(link_text):
            return {
                **base,
                "classification": "category_page",
                "confidence": 88,
                "reason": "Category or demographic listing page, not an individual scholarship",
            }

    if GENERIC_NAV_PATTERNS.search(link_text) and not SPECIFIC_PROGRAM.search(link_text):
        return {
            **base,
            "classification": "category_page",
            "confidence": 82,
            "reason": "Generic scholarship browse/listing navigation",
        }

    # Fastweb-specific
    if host and "fastweb.com" in host:
        if host in APP_STORE_DOMAINS or "itunes" in raw_href.lower() or "/app" in path_lower:
            return {
                **base,
                "classification": "app_store",
                "confidence": 94,
                "reason": "Fastweb app download link",
            }
        if re.search(r"/college-scholarships/featured", path_lower) or path_lower in (
            "/college-scholarships",
            "/scholarships",
        ):
            if not SPECIFIC_PROGRAM.search(link_text):
                return {
                    **base,
                    "classification": "category_page",
                    "confidence": 80,
                    "reason": "Fastweb featured/category listing page",
                }
        if re.search(r"/(browse|search|category|directories)", path_lower):
            return {
                **base,
                "classification": "category_page",
                "confidence": 78,
                "reason": "Fastweb browse/search/category path",
            }

    # Login-only
    if re.search(r"\b(sign\s*in|log\s*in|register|create account)\b", link_text, re.I) and not SPECIFIC_PROGRAM.search(
        link_text
    ):
        if not re.search(r"\bdeadline\b|\$[\d,]+", ctx, re.I):
            return {
                **base,
                "classification": "portal_navigation",
                "confidence": 75,
                "reason": "Login or account navigation without scholarship detail",
            }

    # Marketing
    if re.search(r"\b(unsubscribe|email preferences|privacy policy|terms of use)\b", combined, re.I):
        return {
            **base,
            "classification": "marketing",
            "confidence": 85,
            "reason": "Footer/legal/marketing link",
        }

    # Score positive signals
    confidence = 40
    reasons: list[str] = []

    if SPECIFIC_PROGRAM.search(link_text):
        confidence += 25
        reasons.append("specific program name in title")
    elif INDIVIDUAL_POSITIVE.search(link_text) and len(link_text) > 12:
        confidence += 15
        reasons.append("scholarship program keywords in title")

    if re.search(r"\bdeadline|due date|closes? on|apply by\b", ctx, re.I):
        confidence += 15
        reasons.append("deadline in context")
    if re.search(r"\$[\d,]+|award amount|up to \$", ctx, re.I):
        confidence += 15
        reasons.append("award amount in context")
    if re.search(r"\b(apply|application|eligibility|sponsor|provider)\b", ctx, re.I):
        confidence += 10
        reasons.append("application detail in context")

    if re.search(r"\bapply\b", link_text, re.I) and len(link_text) > 15:
        classification = "application_page"
        confidence += 10
    elif confidence >= 55 and not CATEGORY_TITLE_PATTERNS[0].search(link_text):
        classification = "individual_opportunity"
    else:
        classification = "portal_navigation"
        confidence = min(confidence, 55)
        reasons.append("insufficient evidence of individual opportunity")

    # Path depth heuristic for individual pages
    path_parts = [p for p in path_lower.split("/") if p]
    if host and portal_domain and host.replace("www.", "") == portal_domain.replace("www.", ""):
        if len(path_parts) <= 1 and not reasons:
            classification = "portal_navigation"
            confidence = min(confidence, 50)
            reasons.append("portal homepage or shallow navigation path")

    if len(path_parts) >= 2 and SPECIFIC_PROGRAM.search(link_text):
        confidence += 5

    confidence = max(0, min(100, confidence))
    save = classification in SAVEABLE_CLASSIFICATIONS and confidence >= MIN_SAVE_CONFIDENCE

    reason = "; ".join(reasons) if reasons else (
        "Accepted as individual opportunity" if save else "Does not meet quality threshold"
    )

    return {
        "classification": classification,
        "save": save,
        "confidence": confidence,
        "reason": reason,
        "canonical_url": canonical_url,
        "canonical_domain": canonical_domain,
    }
