import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scholarhive.db")

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

Base.metadata.create_all(bind=engine)
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
