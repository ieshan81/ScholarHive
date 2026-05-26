"""Central trusted platform mode — Scholarship America, Kaleidoscope, Fastweb only by default."""
from __future__ import annotations

import json
from functools import lru_cache
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.discovery_helpers import normalize_url
from app.services.portal_domain import is_blocked_domain, unwrap_google_redirect

DEFAULT_PLATFORMS: list[dict] = [
    {
        "name": "Scholarship America",
        "platform_key": "scholarship_america",
        "allowed_domains": [
            "scholarshipamerica.org",
            "scholarsapply.org",
            "learnmore.scholarsapply.org",
            "apply.scholarsapply.org",
            "portal.scholarshipamerica.org",
            "dollarsforscholars.org",
        ],
        "status": "active",
        "login_required": "sometimes",
    },
    {
        "name": "Kaleidoscope",
        "platform_key": "kaleidoscope",
        "allowed_domains": [
            "mykaleidoscope.com",
            "apply.mykaleidoscope.com",
            "kaleidoscope.com",
        ],
        "status": "active",
        "login_required": "yes",
    },
    {
        "name": "Fastweb",
        "platform_key": "fastweb",
        "allowed_domains": ["fastweb.com", "www.fastweb.com"],
        "status": "active",
        "login_required": "sometimes",
    },
]

DEFAULT_BLOCKED_DOMAINS: dict[str, str] = {
    "scholarowl.com": "Not in trusted platform mode",
    "bold.org": "Not in trusted platform mode",
    "niche.com": "Not in trusted platform mode",
    "scholarships.com": "Not in trusted platform mode",
    "cappex.com": "Not in trusted platform mode",
    "goingmerry.com": "Not in trusted platform mode",
    "unigo.com": "Not in trusted platform mode",
    "careeronestop.org": "Not in trusted platform mode",
    "itunes.apple.com": "Ignored marketing/tracking link",
    "apps.apple.com": "Ignored marketing/tracking link",
    "play.google.com": "Ignored marketing/tracking link",
    "linkedin.com": "Blocked source",
    "facebook.com": "Blocked source",
    "instagram.com": "Blocked source",
    "twitter.com": "Blocked source",
    "x.com": "Blocked source",
    "youtube.com": "Blocked source",
    "tiktok.com": "Blocked source",
    "go.anything.com": "Ignored marketing/tracking link",
    "ablink.r.sofi.com": "Ignored marketing/tracking link",
    "post.spmailtechno.com": "Ignored marketing/tracking link",
    "post.spmailtechnolo.com": "Ignored marketing/tracking link",
    "mail.google.com": "Ignored marketing/tracking link",
    "gmail.com": "Ignored marketing/tracking link",
    "mailchimp.com": "Ignored marketing/tracking link",
    "list-manage.com": "Ignored marketing/tracking link",
}


def trusted_only_enabled() -> bool:
    return get_settings().trusted_only_mode


def _norm_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    return domain.lower().replace("www.", "").strip()


def _host_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        u = url if "://" in url else f"https://{url}"
        return _norm_domain(urlparse(u).netloc)
    except Exception:
        return None


def _load_platforms_from_db(db: Session | None) -> list[dict]:
    if db is None:
        return DEFAULT_PLATFORMS
    try:
        from app.models.trusted_platform import TrustedPlatform

        rows = db.query(TrustedPlatform).filter(TrustedPlatform.status == "active").all()
        if not rows:
            return DEFAULT_PLATFORMS
        return [
            {
                "name": r.name,
                "platform_key": r.platform_key,
                "allowed_domains": r.allowed_domains_json or [],
                "status": r.status,
                "login_required": r.login_required,
            }
            for r in rows
        ]
    except Exception:
        return DEFAULT_PLATFORMS


def _domain_matches_allowed(host: str, allowed: str) -> bool:
    host = _norm_domain(host) or ""
    allowed = _norm_domain(allowed) or ""
    if not host or not allowed:
        return False
    if host == allowed:
        return True
    if host.endswith("." + allowed):
        return True
    if allowed == "kaleidoscope.com" and host.endswith(".mykaleidoscope.com"):
        return True
    if allowed == "mykaleidoscope.com" and host.endswith(".mykaleidoscope.com"):
        return True
    return False


def is_trusted_domain(domain: str | None, db: Session | None = None) -> bool:
    host = _norm_domain(domain)
    if not host:
        return False
    for platform in _load_platforms_from_db(db):
        for allowed in platform.get("allowed_domains", []):
            if _domain_matches_allowed(host, allowed):
                return True
    return False


def get_platform_for_url(url: str | None, db: Session | None = None) -> dict | None:
    host = _host_from_url(canonicalize_platform_url(url))
    if not host:
        return None
    for platform in _load_platforms_from_db(db):
        for allowed in platform.get("allowed_domains", []):
            if _domain_matches_allowed(host, allowed):
                return platform
    return None


def canonicalize_platform_url(url: str | None) -> str | None:
    if not url or not str(url).strip():
        return None
    return unwrap_google_redirect(normalize_url(url.strip()) or url.strip())


def blocked_reason(domain_or_url: str | None, db: Session | None = None) -> str | None:
    host = _host_from_url(domain_or_url) if "://" in (domain_or_url or "") else _norm_domain(domain_or_url)
    if not host:
        return "Invalid URL"
    if is_trusted_domain(host, db):
        return None
    if db:
        try:
            from app.models.trusted_platform import BlockedSource

            row = db.query(BlockedSource).filter(BlockedSource.domain == host).first()
            if row:
                return row.reason
        except Exception:
            pass
    if host in DEFAULT_BLOCKED_DOMAINS:
        return DEFAULT_BLOCKED_DOMAINS[host]
    if is_blocked_domain(host):
        return "Ignored marketing/tracking link"
    if any(x in host for x in ("ablink.", "sendgrid", "mailchimp", "spmailtechno", "click.")):
        return "Ignored marketing/tracking link"
    if trusted_only_enabled():
        return "Not in trusted platform mode"
    return None


def should_create_portal(url: str | None, db: Session | None = None) -> tuple[bool, str | None]:
    if not trusted_only_enabled():
        from app.services.portal_domain import quick_canonical_domain

        domain = quick_canonical_domain(url)
        if not domain or is_blocked_domain(domain):
            return False, blocked_reason(url, db) or "Blocked domain"
        return True, None

    canonical = canonicalize_platform_url(url)
    host = _host_from_url(canonical)
    if not host:
        return False, "Invalid URL"
    if is_trusted_domain(host, db):
        return True, None
    reason = blocked_reason(host, db) or "Not in trusted platform mode"
    return False, reason


def should_create_scholarship(url: str | None, db: Session | None = None) -> tuple[bool, str | None]:
    """Whether a discovery hit may become an active scholarship."""
    ok, reason = should_create_portal(url, db)
    if not ok:
        return False, reason
    if trusted_only_enabled():
        platform = get_platform_for_url(url, db)
        if not platform:
            return False, "Not in trusted platform mode"
    return True, None


def should_create_opportunity(url: str | None, db: Session | None = None) -> tuple[bool, str | None]:
    from app.services.opportunity_quality import classify_portal_link

    ok, reason = should_create_portal(url, db)
    if not ok:
        return False, reason
    platform = get_platform_for_url(url, db)
    quality = classify_portal_link(
        "",
        url or "",
        "",
        final_url=url,
        portal_domain=platform["allowed_domains"][0] if platform else None,
    )
    if quality.get("save"):
        return True, None
    return False, quality.get("reason") or "Does not meet opportunity quality bar"


def trusted_search_queries(profile=None, user_query: str | None = None) -> list[str]:
    """Site-restricted queries for trusted platforms only."""
    if user_query and user_query.strip():
        q = user_query.strip()
        if "site:" in q.lower():
            return [q]
        return [q]

    major = "mechanical engineering"
    intl = "international student"
    stem = "STEM scholarship"
    if profile:
        if profile.major:
            major = profile.major
        if getattr(profile, "international_student", False):
            intl = "international student"

    templates = [
        f"site:scholarshipamerica.org {major} {intl}",
        f"site:scholarsapply.org {major} scholarship undergraduate",
        f"site:learnmore.scholarsapply.org scholarship {intl} {stem}",
        f"site:apply.mykaleidoscope.com scholarship {major}",
        f"site:mykaleidoscope.com scholarship {major}",
        f"site:fastweb.com {major} scholarship",
        f"site:fastweb.com scholarship {intl} {stem}",
    ]
    return templates[:7]


def list_trusted_platforms(db: Session) -> list[dict]:
    platforms = _load_platforms_from_db(db)
    from app.models.portal import Portal

    out = []
    for p in platforms:
        key = p["platform_key"]
        primary_domain = p["allowed_domains"][0] if p.get("allowed_domains") else key
        portal = (
            db.query(Portal)
            .filter(
                (Portal.canonical_domain.in_(p["allowed_domains"]))
                | (Portal.domain.in_(p["allowed_domains"]))
            )
            .first()
        )
        out.append(
            {
                "platform_key": key,
                "name": p["name"],
                "status": p["status"],
                "login_required": p.get("login_required", "unknown"),
                "allowed_domains": p.get("allowed_domains", []),
                "portal_id": portal.id if portal else None,
                "portal_domain": portal.domain if portal else primary_domain,
                "portal_url": portal.portal_url if portal else f"https://{primary_domain}",
                "session_status": portal.session_status if portal else "not_connected",
                "last_scanned_at": portal.last_scanned_at.isoformat()
                if portal and portal.last_scanned_at
                else None,
                "opportunities_discovered": portal.opportunities_discovered if portal else 0,
                "checkpoints_pending": portal.checkpoints_pending if portal else 0,
            }
        )
    return out


def list_ignored_sources(db: Session, limit: int = 100) -> list[dict]:
    from app.models.portal import Portal

    rows = (
        db.query(Portal)
        .filter(Portal.domain_status.in_(("ignored", "tracking", "irrelevant", "blocked")))
        .order_by(Portal.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "domain": r.domain,
            "canonical_domain": r.canonical_domain,
            "domain_status": r.domain_status,
            "portal_url": r.portal_url,
            "reason": blocked_reason(r.domain, db) or "Manual review only",
            "source_count": r.source_count,
        }
        for r in rows
    ]


def trusted_mode_status(db: Session) -> dict:
    return {
        "trusted_only_mode": trusted_only_enabled(),
        "gmail_auto_discovery_paused": trusted_only_enabled(),
        "platforms": [p["name"] for p in _load_platforms_from_db(db)],
        "platform_keys": [p["platform_key"] for p in _load_platforms_from_db(db)],
        "message": (
            "Trusted Platform Mode active: Scholarship America, Kaleidoscope, Fastweb."
            if trusted_only_enabled()
            else "Broad discovery enabled."
        ),
    }
