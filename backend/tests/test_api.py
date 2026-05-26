import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scholarhive.db")

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.db_migrate import run_migrations

Base.metadata.create_all(bind=engine)
run_migrations()
client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "ScholarHive AI"
    assert "database" in data
    assert "gemini_configured" in data


def test_gmail_not_configured():
    r = client.get("/api/gmail/status")
    assert r.status_code == 200
    # Without env vars, should not crash
    assert "configured" in r.json()


def test_telegram_webhook_no_token():
    r = client.post("/api/telegram/webhook", json={"message": {"text": "hello"}})
    assert r.status_code == 200


def test_essay_generate_no_gemini():
    # Ensure scholarship exists from seed
    sch = client.get("/api/scholarships").json()
    if not sch:
        client.post("/api/scholarships", json={"name": "Test", "status": "found"})
        sch = client.get("/api/scholarships").json()
    sid = sch[0]["id"]
    r = client.post("/api/essays/generate", json={"scholarship_id": sid})
    # Either 503 or success if gemini configured in CI
    assert r.status_code in (200, 503)


def test_scholarship_crud():
    r = client.post("/api/scholarships", json={
        "name": "Test Scholarship",
        "source_type": "manual",
        "status": "found",
    })
    assert r.status_code == 200
    sid = r.json()["id"]
    r2 = client.get(f"/api/scholarships/{sid}")
    assert r2.json()["name"] == "Test Scholarship"


def test_eligibility_evaluate():
    sch = client.get("/api/scholarships").json()
    if sch:
        r = client.post(f"/api/scholarships/{sch[0]['id']}/evaluate")
        assert r.status_code == 200
        assert "eligibility_score" in r.json()


def test_health_not_spa_html():
    r = client.get("/health")
    assert "application/json" in r.headers.get("content-type", "")


def test_spa_fallback_deep_links():
    from app.main import INDEX_HTML

    if not INDEX_HTML.is_file():
        return
    for path in ("/", "/profile", "/settings", "/radar", "/queue"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "text/html" in r.headers.get("content-type", "")


def test_unknown_api_path_json_404():
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.json()["detail"] == "Not Found"


def test_web_search_not_configured():
    r = client.get("/api/web-search/status")
    assert r.status_code == 200
    data = r.json()
    assert "configured" in data


def test_health_tavily_field():
    r = client.get("/health")
    assert "tavily_configured" in r.json()


def test_discovery_classifier_listicle():
    from app.services.discovery_classifier import classify_candidate
    cls, conf, _ = classify_candidate("293 Mechanical Engineering Scholarships available in the USA", "")
    assert cls == "scholarship_database_page"
    assert conf > 0.8


def test_telegram_config_save():
    r = client.put("/api/telegram/config", json={"chat_id": "12345"})
    assert r.status_code == 200
    r2 = client.get("/api/telegram/config")
    assert r2.json().get("chat_id") == "12345"


def test_mark_suspects():
    client.post("/api/scholarships", json={"name": "500 Scholarships in USA", "source_type": "web", "status": "found"})
    r = client.post("/api/scholarships/mark-suspects-review")
    assert r.status_code == 200


def test_telegram_diagnostics():
    r = client.get("/api/telegram/diagnostics")
    assert r.status_code == 200
    assert "telegram_configured" in r.json()


def test_telegram_send_test_no_chat():
    r = client.post("/api/telegram/send-test", json={})
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data.get("success") is False or data.get("success") is True


def test_portal_domain_blocks_mail_google():
    from app.services.portal_domain import quick_canonical_domain, is_blocked_domain
    assert is_blocked_domain("mail.google.com")
    assert quick_canonical_domain("https://mail.google.com/mail/u/0/") is None


def test_memory_vault_paste():
    r = client.post(
        "/api/memory-vault/paste",
        json={"text": "I am an international mechanical engineering student at State University with GPA 3.8. " * 3, "title": "Test", "source_type": "essay"},
    )
    assert r.status_code == 200


def test_memory_vault_overview():
    r = client.get("/api/memory-vault/overview")
    assert r.status_code == 200
    assert "clusters" in r.json()


def test_portal_agent_status():
    r = client.get("/api/portals/agent-status")
    assert r.status_code == 200
    data = r.json()
    assert "playwright_available" in data
    assert "chromium_available" in data
    assert "browser_agent" in data
    assert data["final_submit"] == "always_manual"


def test_portal_public_scan_no_crash():
    from app.models.portal import Portal
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        portal = db.query(Portal).filter(Portal.domain == "example.com").first()
        if not portal:
            portal = Portal(domain="example.com", portal_url="https://example.com", portal_name="Example")
            db.add(portal)
            db.commit()
            db.refresh(portal)
        r = client.post(f"/api/portals/{portal.id}/scan-public")
        assert r.status_code == 200
        data = r.json()
        assert "success" in data or "message" in data
        body = r.text
        assert "Sync API inside the asyncio loop" not in body
        if data.get("success") is False:
            assert data.get("error") or data.get("message")
            assert data.get("screenshot_url") is None
    finally:
        db.close()


def test_portal_screenshot_missing_404():
    r = client.get("/api/portals/runs/999999/screenshot")
    assert r.status_code == 404
    assert "not available" in r.json()["detail"].lower()


def test_portal_public_scan_failed_returns_clean_error():
    from unittest.mock import AsyncMock, patch

    from app.services.portal_browser import CheckpointResult, PageScanResult

    with patch("app.services.portal_agent.browser.scan_page", new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = PageScanResult(
            url="https://example.com",
            title="",
            checkpoint=CheckpointResult(False),
            error="Test scan failure",
        )
        from app.models.portal import Portal
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            portal = db.query(Portal).filter(Portal.domain == "example-scan-fail.test").first()
            if not portal:
                portal = Portal(
                    domain="example-scan-fail.test",
                    portal_url="https://example.com",
                    portal_name="Fail Test",
                )
                db.add(portal)
                db.commit()
                db.refresh(portal)
            r = client.post(f"/api/portals/{portal.id}/scan-public")
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is False
            assert data["status"] == "failed"
            assert data["error"] == "Test scan failure"
            assert data.get("screenshot_url") is None
        finally:
            db.close()
