"""Playwright browser layer — async API, no stealth, no CAPTCHA/2FA bypass."""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from app.config import get_settings

logger = logging.getLogger(__name__)

_LAST_ERROR: str | None = None
_CHROMIUM_OK: bool | None = None

# Active browser contexts keyed by portal_run_id (in-process only)
_ACTIVE: dict[int, dict[str, Any]] = {}

CHECKPOINT_PATTERNS = [
    (r"sign\s*in|log\s*in|login required", "login_required"),
    (r"continue with google|sign in with google", "google_consent"),
    (r"captcha|i am not a robot|recaptcha|hcaptcha", "captcha"),
    (r"two[- ]?factor|2fa|verification code|enter code", "two_factor"),
    (r"verify your email|confirm your email", "email_verification"),
    (r"submit application|final submit|i certify|signature required", "final_submit"),
    (r"payment required|pay now|checkout", "payment"),
]

SCHOLARSHIP_LINK_HINTS = re.compile(
    r"scholarship|fellowship|grant|award|apply|application|bursary|financial.?aid",
    re.I,
)
JUNK_LINK_HINTS = re.compile(
    r"privacy|terms|cookie|facebook|twitter|instagram|linkedin\.com/company|unsubscribe|blog\b|news\b",
    re.I,
)
DEADLINE_HINT = re.compile(
    r"deadline|due date|closes? on|apply by|submission date",
    re.I,
)
AWARD_HINT = re.compile(r"\$[\d,]+|usd\s*[\d,]+|award amount|up to \$", re.I)


@dataclass
class CheckpointResult:
    detected: bool
    checkpoint_type: str | None = None
    reason: str | None = None


@dataclass
class ExtractedLink:
    text: str
    href: str
    link_type: str
    context: str = ""
    deadline_hint: str | None = None
    award_hint: str | None = None


@dataclass
class PageScanResult:
    url: str
    title: str
    checkpoint: CheckpointResult
    links: list[ExtractedLink] = field(default_factory=list)
    screenshot_path: str | None = None
    login_required: bool = False
    error: str | None = None


def _base_data_dir() -> Path:
    settings = get_settings()
    root = Path(settings.upload_storage_path).parent
    if settings.storage_writable:
        return root
    return Path(os.environ.get("TEMP", "/tmp")) / "scholarhive-data"


def ensure_browser_dirs() -> dict[str, Any]:
    base = _base_data_dir()
    sessions = base / "portal-sessions"
    screenshots = base / "portal-screenshots"
    artifacts = base / "portal-artifacts"
    writable = True
    try:
        for d in (sessions, screenshots, artifacts):
            d.mkdir(parents=True, exist_ok=True)
            test = d / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
    except OSError as exc:
        writable = False
        logger.warning("Portal browser dirs not writable: %s", exc)
    return {
        "sessions_dir": str(sessions),
        "screenshots_dir": str(screenshots),
        "artifacts_dir": str(artifacts),
        "writable": writable,
    }


def session_storage_path(portal_account_id: int) -> Path:
    dirs = ensure_browser_dirs()
    return Path(dirs["sessions_dir"]) / f"account_{portal_account_id}.json"


def screenshot_path(run_id: int) -> Path:
    dirs = ensure_browser_dirs()
    return Path(dirs["screenshots_dir"]) / f"run_{run_id}.png"


def screenshot_exists(run_id: int) -> bool:
    return screenshot_path(run_id).is_file()


async def check_playwright_available() -> dict[str, Any]:
    global _LAST_ERROR, _CHROMIUM_OK
    settings = get_settings()
    if os.environ.get("PLAYWRIGHT_ENABLED", "true").lower() in ("0", "false", "no"):
        return {
            "playwright_available": False,
            "chromium_available": False,
            "last_error": "PLAYWRIGHT_ENABLED=false",
        }

    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except Exception as exc:
        _LAST_ERROR = f"playwright import failed: {exc}"
        _CHROMIUM_OK = False
        return {"playwright_available": False, "chromium_available": False, "last_error": _LAST_ERROR}

    if _CHROMIUM_OK is not None:
        return {
            "playwright_available": True,
            "chromium_available": _CHROMIUM_OK,
            "last_error": _LAST_ERROR if not _CHROMIUM_OK else None,
        }

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto("https://example.com", timeout=20000, wait_until="domcontentloaded")
            await page.close()
            await ctx.close()
            await browser.close()
        _CHROMIUM_OK = True
        _LAST_ERROR = None
    except Exception as exc:
        _CHROMIUM_OK = False
        _LAST_ERROR = str(exc)

    return {
        "playwright_available": True,
        "chromium_available": _CHROMIUM_OK,
        "last_error": _LAST_ERROR,
    }


def _browser_mode() -> str:
    settings = get_settings()
    if settings.is_production:
        return "railway"
    return "local"


async def _launch_browser(headed: bool = False):
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=not headed,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    return pw, browser


async def _new_context(browser, storage_state: str | None = None):
    opts: dict[str, Any] = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": "ScholarHivePortalAgent/1.0",
    }
    if storage_state and Path(storage_state).is_file():
        opts["storage_state"] = storage_state
    return await browser.new_context(**opts)


async def detect_checkpoint(page) -> CheckpointResult:
    try:
        body = ((await page.inner_text("body")) or "")[:15000].lower()
        url = (page.url or "").lower()
        combined = f"{body} {url}"
        for pattern, ctype in CHECKPOINT_PATTERNS:
            if re.search(pattern, combined, re.I):
                return CheckpointResult(
                    detected=True,
                    checkpoint_type=ctype,
                    reason=f"Detected signal: {ctype.replace('_', ' ')}",
                )
        if await page.locator('input[type="password"]').count() > 0 and re.search(
            r"sign|log\s*in", combined
        ):
            return CheckpointResult(True, "login_required", "Password field on page")
    except Exception as exc:
        logger.debug("checkpoint detect error: %s", exc)
    return CheckpointResult(False)


async def detect_login_required(page) -> bool:
    cp = await detect_checkpoint(page)
    return cp.detected and cp.checkpoint_type in (
        "login_required",
        "google_consent",
        "captcha",
        "two_factor",
        "email_verification",
    )


async def take_screenshot(page, run_id: int) -> str | None:
    path = screenshot_path(run_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path), full_page=False)
        return str(path)
    except Exception as exc:
        logger.warning("screenshot failed: %s", exc)
        return None


def _classify_link(text: str, href: str) -> str:
    t = f"{text} {href}".lower()
    if JUNK_LINK_HINTS.search(t):
        return "irrelevant"
    if re.search(r"sign.?in|log.?in|oauth|auth", t):
        return "login_link"
    if re.search(r"apply|application", t) and SCHOLARSHIP_LINK_HINTS.search(t):
        return "application_link"
    if SCHOLARSHIP_LINK_HINTS.search(t):
        return "scholarship_detail"
    if re.search(r"scholarships|browse|search|directory", t):
        return "portal_navigation"
    return "irrelevant"


async def extract_links(page, base_url: str) -> list[ExtractedLink]:
    results: list[ExtractedLink] = []
    seen: set[str] = set()
    try:
        anchors = await page.eval_on_selector_all(
            "a[href]",
            """els => els.slice(0, 200).map(a => ({
                text: (a.innerText || '').trim().slice(0, 200),
                href: a.href
            }))""",
        )
        page_text = ((await page.inner_text("body")) or "")[:5000]
        deadline_m = DEADLINE_HINT.search(page_text)
        award_m = AWARD_HINT.search(page_text)
        deadline_hint = deadline_m.group(0) if deadline_m else None
        award_hint = award_m.group(0) if award_m else None

        for item in anchors or []:
            href = (item.get("href") or "").strip()
            text = (item.get("text") or "").strip()
            if not href or href.startswith("javascript:") or href in seen:
                continue
            seen.add(href)
            if not href.startswith("http"):
                href = urljoin(base_url, href)
            link_type = _classify_link(text, href)
            if link_type == "irrelevant":
                continue
            results.append(
                ExtractedLink(
                    text=text or href[:80],
                    href=href,
                    link_type=link_type,
                    context=page_text[:300],
                    deadline_hint=deadline_hint,
                    award_hint=award_hint,
                )
            )
    except Exception as exc:
        logger.warning("extract_links error: %s", exc)
    return results


async def extract_form_fields(page) -> dict[str, Any]:
    """Foundation for ApplicationFormDraft — read-only, no submit."""
    fields: list[dict] = []
    essays: list[dict] = []
    uploads: list[dict] = []
    try:
        inputs = await page.eval_on_selector_all(
            "input, textarea, select",
            """els => els.slice(0, 80).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                name: el.name || el.id || '',
                label: (el.labels && el.labels[0] ? el.labels[0].innerText : '') || el.placeholder || '',
                required: el.required || false
            }))""",
        )
        for inp in inputs or []:
            tag = inp.get("tag", "")
            label = (inp.get("label") or inp.get("name") or "").lower()
            entry = {
                "tag": tag,
                "type": inp.get("type"),
                "name": inp.get("name"),
                "label": inp.get("label"),
                "required": inp.get("required"),
            }
            fields.append(entry)
            if tag == "textarea" or "essay" in label or "statement" in label:
                essays.append(entry)
            if inp.get("type") == "file":
                uploads.append(entry)

        submit_buttons = await page.eval_on_selector_all(
            'button[type="submit"], input[type="submit"]',
            "els => els.map(e => (e.innerText || e.value || 'Submit').trim())",
        )
    except Exception:
        submit_buttons = []

    return {
        "fields": fields,
        "essays_needed": essays,
        "documents_needed": uploads,
        "submit_buttons": submit_buttons or [],
        "human_checkpoint_required": bool(submit_buttons),
    }


async def _close_browser_objects(page=None, context=None, browser=None, pw=None) -> None:
    for obj in (page, context, browser):
        if obj:
            try:
                await obj.close()
            except Exception:
                pass
    if pw:
        try:
            await pw.stop()
        except Exception:
            pass


async def scan_page(
    url: str,
    run_id: int | None = None,
    storage_state: str | None = None,
    headed: bool = False,
) -> PageScanResult:
    check = await check_playwright_available()
    if not check.get("chromium_available"):
        return PageScanResult(
            url=url,
            title="",
            checkpoint=CheckpointResult(False),
            error=check.get("last_error") or "Chromium not available",
        )

    pw = None
    browser = None
    context = None
    page = None
    try:
        headed = headed and _browser_mode() == "local"
        pw, browser = await _launch_browser(headed=headed)
        context = await _new_context(browser, storage_state)
        page = await context.new_page()
        page.set_default_timeout(30000)
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1500)

        checkpoint = await detect_checkpoint(page)
        final_url = page.url
        title = (await page.title()) or ""
        links = await extract_links(page, final_url)
        login_required = await detect_login_required(page)
        shot = await take_screenshot(page, run_id) if run_id else None

        if run_id is not None:
            _ACTIVE[run_id] = {"playwright": pw, "browser": browser, "context": context, "page": page}
        else:
            await _close_browser_objects(page, context, browser, pw)

        return PageScanResult(
            url=final_url,
            title=title,
            checkpoint=checkpoint,
            links=links,
            screenshot_path=shot,
            login_required=login_required,
        )
    except Exception as exc:
        await _close_browser_objects(page, context, browser, pw)
        if run_id and run_id in _ACTIVE:
            del _ACTIVE[run_id]
        err = str(exc)
        if "Sync API inside the asyncio loop" in err:
            err = "Playwright async API misconfiguration — report to maintainer"
        return PageScanResult(
            url=url,
            title="",
            checkpoint=CheckpointResult(False),
            error=err,
        )


async def save_storage_state(run_id: int, portal_account_id: int) -> dict[str, Any]:
    active = _ACTIVE.get(run_id)
    if not active or not active.get("context"):
        path = session_storage_path(portal_account_id)
        if path.is_file():
            return {"success": True, "path": str(path), "message": "Using existing saved session file"}
        return {
            "success": False,
            "message": (
                "Session cannot be captured from your external browser yet. "
                "Start a browser session in ScholarHive, complete login in the controlled browser "
                "(local dev), or use Scan public page first."
            ),
        }

    path = session_storage_path(portal_account_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        await active["context"].storage_state(path=str(path))
        await close_run_browser(run_id)
        return {"success": True, "path": str(path), "message": "Session storage saved"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


async def close_run_browser(run_id: int) -> None:
    active = _ACTIVE.pop(run_id, None)
    if not active:
        return
    await _close_browser_objects(
        active.get("page"),
        active.get("context"),
        active.get("browser"),
        active.get("playwright"),
    )


def has_active_browser(run_id: int) -> bool:
    return run_id in _ACTIVE
