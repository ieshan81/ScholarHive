"""Tests for portal opportunity quality classification."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scholarhive.db")

from app.services.opportunity_quality import classify_portal_link
from app.services.portal_domain import unwrap_google_redirect, quick_canonical_domain


def test_itunes_fastweb_app_rejected():
    r = classify_portal_link(
        "Fastweb College Scholarships App",
        "https://itunes.apple.com/us/app/fastweb-college-scholarships/id346342732",
        "",
        portal_domain="fastweb.com",
    )
    assert r["classification"] == "app_store"
    assert r["save"] is False
    assert r["confidence"] >= 65


def test_hispanic_category_rejected():
    r = classify_portal_link(
        "Scholarships for Hispanic Students",
        "https://www.fastweb.com/college-scholarships/scholarships-for-hispanic-students",
        "Browse scholarships by demographic",
        portal_domain="fastweb.com",
    )
    assert r["classification"] == "category_page"
    assert r["save"] is False


def test_veterans_category_rejected():
    r = classify_portal_link(
        "Scholarships for Veterans",
        "https://www.fastweb.com/college-scholarships/veterans",
        "",
        portal_domain="fastweb.com",
    )
    assert r["classification"] == "category_page"
    assert r["save"] is False


def test_linkedin_social_rejected():
    r = classify_portal_link(
        "LinkedIn",
        "https://www.linkedin.com/company/fastweb/",
        "",
    )
    assert r["classification"] == "social"
    assert r["save"] is False


def test_donate_rejected():
    r = classify_portal_link(
        "Donate",
        "https://www.islamicity.org/donate/",
        "Support our mission",
    )
    assert r["classification"] == "donation"
    assert r["save"] is False


def test_sofi_tracking_rejected():
    r = classify_portal_link(
        "View offer",
        "https://ablink.r.sofi.com/ls/click?upn=abc",
        "",
    )
    assert r["classification"] == "tracking_link"
    assert r["save"] is False


def test_spmailtechno_tracking_rejected():
    r = classify_portal_link(
        "Scholarship alert",
        "https://post.spmailtechno.com/click/xyz",
        "",
    )
    assert r["classification"] == "tracking_link"
    assert r["save"] is False


def test_real_scholarship_accepted():
    r = classify_portal_link(
        "The Gates Scholarship Program",
        "https://www.fastweb.com/scholarships/the-gates-scholarship",
        "Deadline: January 15. Award amount: $50,000. Apply for this prestigious program.",
        portal_domain="fastweb.com",
    )
    assert r["classification"] in ("individual_opportunity", "application_page")
    assert r["save"] is True
    assert r["confidence"] >= 65


def test_featured_scholarships_category_rejected():
    r = classify_portal_link(
        "Featured Scholarships",
        "https://www.fastweb.com/college-scholarships/featured-scholarships",
        "",
        portal_domain="fastweb.com",
    )
    assert r["classification"] == "category_page"
    assert r["save"] is False


def test_google_url_unwrap():
    wrapped = "https://www.google.com/url?q=https%3A%2F%2Fwww.example.org%2Fstem-scholarship"
    unwrapped = unwrap_google_redirect(wrapped)
    assert "example.org" in unwrapped
    domain = quick_canonical_domain(unwrapped)
    assert domain == "example.org"
