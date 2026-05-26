"""Trusted platform mode tests."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scholarhive.db")

from fastapi.testclient import TestClient

from app.main import app
from app.services.trusted_platforms import (
    blocked_reason,
    is_trusted_domain,
    should_create_portal,
    trusted_only_enabled,
    trusted_search_queries,
)

client = TestClient(app)


def test_scholarshipamerica_trusted():
    assert is_trusted_domain("scholarshipamerica.org")
    assert is_trusted_domain("scholarsapply.org")


def test_kaleidoscope_trusted():
    assert is_trusted_domain("apply.mykaleidoscope.com")
    assert is_trusted_domain("mykaleidoscope.com")


def test_fastweb_trusted():
    assert is_trusted_domain("fastweb.com")
    assert is_trusted_domain("www.fastweb.com")


def test_scholarowl_blocked():
    assert not is_trusted_domain("scholarowl.com")
    assert "trusted" in (blocked_reason("scholarowl.com") or "").lower()


def test_bold_blocked():
    assert not is_trusted_domain("bold.org")


def test_sofi_tracking_ignored():
    assert not is_trusted_domain("ablink.r.sofi.com")


def test_mail_google_ignored():
    assert not is_trusted_domain("mail.google.com")


def test_itunes_ignored():
    assert not is_trusted_domain("itunes.apple.com")


def test_should_not_create_portal_unknown():
    ok, reason = should_create_portal("https://scholarowl.com/foo")
    assert ok is False
    assert reason


def test_trusted_search_queries_site_restricted():
    queries = trusted_search_queries()
    assert any("site:fastweb.com" in q for q in queries)
    assert any("site:scholarsapply.org" in q for q in queries)
    assert all("site:" in q for q in queries)


def test_gmail_scan_paused_in_trusted_mode():
    if not trusted_only_enabled():
        return
    r = client.post("/api/gmail/scan?days=7")
    assert r.status_code == 200
    data = r.json()
    assert data.get("paused") is True or "paused" in (data.get("message") or "").lower()


def test_trusted_platform_status_endpoint():
    r = client.get("/api/trusted-platforms/status")
    assert r.status_code == 200
    assert r.json().get("trusted_only_mode") is True


def test_portal_list_default_trusted_only():
    r = client.get("/api/portals")
    assert r.status_code == 200
    domains = {p["domain"] for p in r.json()}
    if domains:
        for d in domains:
            assert is_trusted_domain(d.replace("www.", ""))


def test_apply_cleanup_endpoint():
    r = client.post("/api/trusted-platforms/apply-cleanup")
    assert r.status_code == 200
    data = r.json()
    assert "trusted_portals_active" in data
    assert data.get("gmail_auto_discovery_paused") is True


def test_trusted_platform_list_has_three_defaults():
    r = client.get("/api/trusted-platforms")
    assert r.status_code == 200
    keys = {p["platform_key"] for p in r.json()}
    assert "scholarship_america" in keys
    assert "kaleidoscope" in keys
    assert "fastweb" in keys
