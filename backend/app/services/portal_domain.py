"""Portal domain canonicalization — strip tracking, resolve redirects, block junk."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.services.discovery_helpers import normalize_url

BLOCKED_PORTAL_DOMAINS = frozenset({
    "mail.google.com",
    "gmail.com",
    "google.com",
    "accounts.google.com",
    "mail.com",
    "outlook.com",
    "live.com",
    "yahoo.com",
    "sendgrid.net",
    "sendgrid.com",
    "list-manage.com",
    "click.mailchimp.com",
    "mandrillapp.com",
    "hubspotlinks.com",
    "hubspotemail.net",
    "customeriomail.com",
    "trk.mailgun.net",
    "email.mg",
    "awstrack.me",
    "amazonaws.com",
    "cloudfront.net",
    "doubleclick.net",
    "googlesyndication.com",
    "go.anything.com",
    "ablink.r.sofi.com",
    "post.spmailtechno.com",
    "linkedin.com",
    "itunes.apple.com",
    "apps.apple.com",
    "play.google.com",
})

TRACKING_DOMAIN_SUBSTRINGS = (
    "click.", "track.", "trk.", "links.", "email.", "redirect.",
    "awstrack", "sendgrid", "mailchimp", "list-manage", "hubspot",
    "mandrill", "customer.io", "ct.send", "urldefense", "safelinks",
)

GOOGLE_REDIRECT_HOSTS = frozenset({"google.com", "www.google.com"})


def _netloc(url: str) -> str | None:
    try:
        p = urlparse(url if "://" in url else f"https://{url}")
        host = (p.netloc or "").lower().replace("www.", "")
        return host or None
    except Exception:
        return None


def is_blocked_domain(domain: str | None) -> bool:
    if not domain:
        return True
    d = domain.lower().replace("www.", "")
    if d in BLOCKED_PORTAL_DOMAINS:
        return True
    if any(sub in d for sub in TRACKING_DOMAIN_SUBSTRINGS):
        return True
    if d.endswith(".amazonaws.com"):
        return True
    return False


def unwrap_google_redirect(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().replace("www.", "")
    if host in GOOGLE_REDIRECT_HOSTS and parsed.path in ("/url", "/url/"):
        qs = parse_qs(parsed.query)
        for key in ("url", "q", "u"):
            if qs.get(key):
                return unquote(qs[key][0])
    return url


def quick_canonical_domain(url: str | None) -> str | None:
    """Sync canonicalization without network — unwrap known redirects, strip tracking."""
    if not url or not str(url).strip():
        return None
    u = unwrap_google_redirect(normalize_url(url.strip()) or url.strip())
    domain = _netloc(u)
    if not domain or is_blocked_domain(domain):
        return None
    return domain


async def resolve_portal_domain(url: str | None, follow_redirects: bool = True) -> tuple[str | None, str | None]:
    """
    Returns (canonical_domain, skip_reason).
    skip_reason set when domain should not become a portal row.
    """
    if not url or not str(url).strip():
        return None, "empty_url"

    current = unwrap_google_redirect(normalize_url(url.strip()) or url.strip())
    domain = _netloc(current)

    if domain and not is_blocked_domain(domain):
        return domain, None

    if not follow_redirects:
        return None, "blocked_or_tracking"

    try:
        async with httpx.AsyncClient(
            timeout=8.0,
            follow_redirects=True,
            max_redirects=5,
            headers={"User-Agent": "ScholarHive/1.0 (+https://scholarhive)"},
        ) as client:
            resp = await client.head(current, follow_redirects=True)
            if resp.status_code >= 400:
                resp = await client.get(current, follow_redirects=True)
            final = str(resp.url)
            final = unwrap_google_redirect(final)
            final_domain = _netloc(final)
            if final_domain and not is_blocked_domain(final_domain):
                return final_domain, None
            return None, "blocked_after_redirect"
    except Exception:
        if domain and not is_blocked_domain(domain):
            return domain, None
        return None, "resolve_failed"
