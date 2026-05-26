"""Portal Agent — Playwright-backed safe browser automation."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.portal import (
    ApplicationFormDraft,
    Portal,
    PortalAccount,
    PortalCheckpoint,
    PortalOpportunity,
    PortalRun,
    PortalSession,
)
from app.services import portal_browser as browser
from app.services.portal_domain import quick_canonical_domain


def portal_agent_status() -> dict:
    settings = get_settings()
    check = browser.check_playwright_available()
    dirs = browser.ensure_browser_dirs()
    mode = browser._browser_mode()

    available = bool(check.get("chromium_available"))
    message = "Playwright Chromium ready for portal scans."
    if not check.get("playwright_available"):
        message = (
            f"Playwright unavailable: {check.get('last_error')}. "
            "Ensure Railway build runs playwright install chromium and system libs (libstdc++)."
        )
    elif not available:
        message = (
            f"Playwright/Chromium not available: {check.get('last_error')}. "
            "Check Railway build logs for `playwright install chromium`."
        )

    return {
        "browser_agent": "playwright" if available else "fallback",
        "playwright_available": check.get("playwright_available", False),
        "chromium_available": available,
        "storage_writable": dirs.get("writable", False),
        "storage_paths": {
            "sessions": dirs.get("sessions_dir"),
            "screenshots": dirs.get("screenshots_dir"),
        },
        "mode": mode,
        "message": message,
        "last_error": check.get("last_error"),
        "safe_limits": [
            "No CAPTCHA/2FA bypass",
            "No stealth or fingerprint evasion",
            "No final application submit",
            "Human checkpoint for login, payment, signature",
            "Cookies never exposed via API",
        ],
        "autonomy_mode_default": "maximum_safe_autonomy",
        "final_submit": "always_manual",
    }


def _get_or_create_account(db: Session, portal: Portal) -> PortalAccount:
    account = db.query(PortalAccount).filter(PortalAccount.portal_id == portal.id).first()
    if not account:
        account = PortalAccount(
            portal_id=portal.id,
            domain=portal.domain,
            portal_url=portal.portal_url,
            provider_name=portal.portal_name or portal.domain,
            auth_status="not_connected",
        )
        db.add(account)
        db.flush()
    return account


def _latest_session(db: Session, account_id: int) -> PortalSession | None:
    return (
        db.query(PortalSession)
        .filter(PortalSession.portal_account_id == account_id)
        .order_by(PortalSession.updated_at.desc())
        .first()
    )


def _session_file(account_id: int) -> str | None:
    path = browser.session_storage_path(account_id)
    return str(path) if path.is_file() else None


def _notify_checkpoint(db: Session, message: str) -> None:
    try:
        import asyncio
        from app.services.telegram_config import get_chat_id
        from app.services.telegram import send_message

        chat_id = get_chat_id(db)
        if not chat_id:
            return
        text = message[:4000]

        async def _send():
            await send_message(chat_id, text)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_send())
        except RuntimeError:
            asyncio.run(_send())
    except Exception:
        pass


def _create_checkpoint(
    db: Session,
    account: PortalAccount,
    run: PortalRun,
    checkpoint_type: str,
    url: str,
    instruction: str,
) -> PortalCheckpoint:
    cp = PortalCheckpoint(
        portal_account_id=account.id,
        checkpoint_type=checkpoint_type,
        current_url=url,
        instruction_to_user=instruction,
        status="pending",
    )
    db.add(cp)
    db.flush()
    run.checkpoint_id = cp.id
    run.status = "human_checkpoint_required"
    run.current_url = url
    portal = db.query(Portal).filter(Portal.id == account.portal_id).first()
    if portal:
        portal.checkpoints_pending = (portal.checkpoints_pending or 0) + 1
    _notify_checkpoint(db, f"ScholarHive Portal checkpoint ({checkpoint_type}): {instruction}\nURL: {url}")
    return cp


def _save_opportunities(
    db: Session,
    account: PortalAccount,
    run: PortalRun,
    links: list,
    portal: Portal,
) -> int:
    saved = 0
    for link in links:
        if link.link_type not in ("scholarship_detail", "application_link"):
            continue
        title = (link.text or "Scholarship opportunity")[:500]
        if len(title) < 5:
            continue
        domain = quick_canonical_domain(link.href)
        existing = (
            db.query(PortalOpportunity)
            .filter(PortalOpportunity.portal_account_id == account.id, PortalOpportunity.title == title)
            .first()
        )
        if existing:
            continue
        opp = PortalOpportunity(
            portal_account_id=account.id,
            portal_run_id=run.id,
            title=title,
            provider=portal.portal_name or portal.domain,
            portal_url=link.href,
            application_url=link.href if link.link_type == "application_link" else None,
            deadline=link.deadline_hint,
            award_amount=link.award_hint,
            eligibility_summary=link.context[:500] if link.context else None,
            status_in_portal="discovered",
            extracted_fields_json={"link_type": link.link_type, "href": link.href},
        )
        db.add(opp)
        saved += 1
    if saved:
        portal.opportunities_discovered = (portal.opportunities_discovered or 0) + saved
    return saved


def _run_to_dict(run: PortalRun, checkpoint: PortalCheckpoint | None = None) -> dict:
    audit = {}
    if run.audit_log_summary:
        try:
            audit = json.loads(run.audit_log_summary)
        except Exception:
            audit = {"summary": run.audit_log_summary}
    return {
        "id": run.id,
        "portal_account_id": run.portal_account_id,
        "status": run.status,
        "current_url": run.current_url,
        "checkpoint_id": run.checkpoint_id,
        "opportunities_found": run.opportunities_found,
        "forms_found": run.forms_found,
        "errors": run.errors,
        "latest_screenshot_path": getattr(run, "latest_screenshot_path", None),
        "browser_mode": getattr(run, "browser_mode", None),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "audit": audit,
        "checkpoint": {
            "id": checkpoint.id,
            "type": checkpoint.checkpoint_type,
            "instruction": checkpoint.instruction_to_user,
            "status": checkpoint.status,
        }
        if checkpoint
        else None,
    }


def start_browser_session(db: Session, portal_id: int) -> dict:
    portal = db.query(Portal).filter(Portal.id == portal_id).first()
    if not portal:
        return {"success": False, "message": "Portal not found"}

    url = portal.portal_url or f"https://{portal.domain}"
    account = _get_or_create_account(db, portal)
    run = PortalRun(
        portal_account_id=account.id,
        status="running",
        current_url=url,
        browser_mode=browser._browser_mode(),
        audit_log_summary=json.dumps({"action": "start_browser_session"}),
    )
    db.add(run)
    db.flush()

    scan = browser.scan_page(url, run_id=run.id, storage_state=_session_file(account.id))
    run.current_url = scan.url or url
    if getattr(run, "latest_screenshot_path", None) is not None or scan.screenshot_path:
        run.latest_screenshot_path = scan.screenshot_path

    if scan.error:
        run.status = "failed"
        run.errors = scan.error
        run.finished_at = datetime.utcnow()
        browser.close_run_browser(run.id)
        db.commit()
        return {
            "success": False,
            "portal_id": portal_id,
            "portal_account_id": account.id,
            "portal_run_id": run.id,
            "status": "failed",
            "message": scan.error,
            "agent_status": portal_agent_status(),
        }

    checkpoint = None
    if scan.checkpoint.detected:
        ctype = scan.checkpoint.checkpoint_type or "login_required"
        if ctype in ("captcha", "two_factor", "final_submit", "payment"):
            browser.close_run_browser(run.id)
        instruction = (
            f"Complete {ctype.replace('_', ' ')} manually at: {scan.url}. "
            "Do not bypass CAPTCHA/2FA. When done, click Continue after checkpoint."
        )
        checkpoint = _create_checkpoint(db, account, run, ctype, scan.url, instruction)
    else:
        run.status = "running"
        run.audit_log_summary = json.dumps(
            {"action": "started", "title": scan.title, "links": len(scan.links)}
        )

    db.commit()
    return {
        "success": True,
        "portal_id": portal_id,
        "portal_account_id": account.id,
        "portal_run_id": run.id,
        "checkpoint_id": checkpoint.id if checkpoint else None,
        "current_url": run.current_url,
        "screenshot_url": f"/api/portals/runs/{run.id}/screenshot",
        "status": run.status,
        "message": checkpoint.instruction_to_user if checkpoint else "Browser session started",
        "agent_status": portal_agent_status(),
    }


def scan_public_portal(db: Session, portal_id: int) -> dict:
    portal = db.query(Portal).filter(Portal.id == portal_id).first()
    if not portal:
        return {"success": False, "message": "Portal not found"}

    url = portal.portal_url or f"https://{portal.domain}"
    account = _get_or_create_account(db, portal)
    run = PortalRun(
        portal_account_id=account.id,
        status="running",
        current_url=url,
        browser_mode=browser._browser_mode(),
        audit_log_summary=json.dumps({"action": "scan_public"}),
    )
    db.add(run)
    db.flush()

    scan = browser.scan_page(url, run_id=run.id)
    browser.close_run_browser(run.id)

    if scan.error:
        run.status = "failed"
        run.errors = scan.error
        run.finished_at = datetime.utcnow()
        db.commit()
        return {"success": False, "message": scan.error, "run_id": run.id}

    checkpoint = None
    if scan.checkpoint.detected and scan.checkpoint.checkpoint_type in (
        "captcha",
        "two_factor",
        "final_submit",
        "payment",
    ):
        checkpoint = _create_checkpoint(
            db,
            account,
            run,
            scan.checkpoint.checkpoint_type,
            scan.url,
            scan.checkpoint.reason or "Human checkpoint required",
        )
    else:
        saved = _save_opportunities(db, account, run, scan.links, portal)
        run.opportunities_found = saved
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        portal.last_scanned_at = datetime.utcnow()
        if scan.login_required:
            portal.login_required = "yes"
        run.latest_screenshot_path = scan.screenshot_path
        run.audit_log_summary = json.dumps(
            {
                "links_found": len(scan.links),
                "opportunities_saved": saved,
                "login_required": scan.login_required,
            }
        )

    db.commit()
    return {
        "success": True,
        "run_id": run.id,
        "status": run.status,
        "opportunities_found": run.opportunities_found,
        "links_extracted": len(scan.links),
        "login_required": scan.login_required,
        "checkpoint_id": checkpoint.id if checkpoint else None,
        "screenshot_url": f"/api/portals/runs/{run.id}/screenshot",
        "message": "Public scan complete" if run.status == "completed" else "Checkpoint required",
    }


def scan_with_session(db: Session, portal_id: int) -> dict:
    portal = db.query(Portal).filter(Portal.id == portal_id).first()
    if not portal:
        return {"success": False, "message": "Portal not found"}

    account = _get_or_create_account(db, portal)
    storage = _session_file(account.id)
    if not storage:
        run = PortalRun(portal_account_id=account.id, status="human_checkpoint_required")
        db.add(run)
        db.flush()
        cp = _create_checkpoint(
            db,
            account,
            run,
            "login_required",
            portal.portal_url or f"https://{portal.domain}",
            "No saved session. Start browser session and save session after manual login.",
        )
        db.commit()
        return {
            "success": False,
            "status": "human_checkpoint_required",
            "checkpoint_id": cp.id,
            "run_id": run.id,
            "message": "No saved session — login required",
        }

    url = portal.portal_url or f"https://{portal.domain}"
    run = PortalRun(
        portal_account_id=account.id,
        status="running",
        current_url=url,
        browser_mode=browser._browser_mode(),
    )
    db.add(run)
    db.flush()

    scan = browser.scan_page(url, run_id=run.id, storage_state=storage)
    browser.close_run_browser(run.id)

    if scan.error:
        run.status = "failed"
        run.errors = scan.error
        db.commit()
        return {"success": False, "message": scan.error}

    if scan.checkpoint.detected:
        cp = _create_checkpoint(
            db,
            account,
            run,
            scan.checkpoint.checkpoint_type or "login_required",
            scan.url,
            "Session may be expired. Log in again and save session.",
        )
        account.auth_status = "expired"
        db.commit()
        return {"success": False, "status": "human_checkpoint_required", "checkpoint_id": cp.id}

    saved = _save_opportunities(db, account, run, scan.links, portal)
    run.opportunities_found = saved
    run.status = "completed"
    run.finished_at = datetime.utcnow()
    portal.last_scanned_at = datetime.utcnow()
    account.auth_status = "connected"
    sess = _latest_session(db, account.id)
    if sess:
        sess.session_status = "active"
        sess.last_used_at = datetime.utcnow()
    db.commit()
    return {
        "success": True,
        "run_id": run.id,
        "opportunities_found": saved,
        "message": f"Session scan complete — {saved} opportunities",
    }


def continue_after_checkpoint(db: Session, run_id: int) -> dict:
    run = db.query(PortalRun).filter(PortalRun.id == run_id).first()
    if not run:
        return {"success": False, "message": "Run not found"}

    checkpoint = None
    if run.checkpoint_id:
        checkpoint = db.query(PortalCheckpoint).filter(PortalCheckpoint.id == run.checkpoint_id).first()
        if checkpoint:
            checkpoint.status = "completed"
            checkpoint.completed_at = datetime.utcnow()

    account = db.query(PortalAccount).filter(PortalAccount.id == run.portal_account_id).first()
    portal = db.query(Portal).filter(Portal.id == account.portal_id).first() if account else None
    if not portal or not account:
        return {"success": False, "message": "Portal account not found"}

    url = run.current_url or portal.portal_url or f"https://{portal.domain}"
    storage = _session_file(account.id)
    scan = browser.scan_page(url, run_id=run.id, storage_state=storage)
    browser.close_run_browser(run.id)

    if scan.checkpoint.detected and scan.checkpoint.checkpoint_type in (
        "captcha",
        "two_factor",
        "final_submit",
    ):
        cp = _create_checkpoint(
            db,
            account,
            run,
            scan.checkpoint.checkpoint_type,
            scan.url,
            "Checkpoint still active — complete manually",
        )
        db.commit()
        return {"success": False, "status": "human_checkpoint_required", "checkpoint_id": cp.id}

    saved = _save_opportunities(db, account, run, scan.links, portal)
    run.opportunities_found = (run.opportunities_found or 0) + saved
    run.status = "completed"
    run.finished_at = datetime.utcnow()
    if portal:
        portal.checkpoints_pending = max(0, (portal.checkpoints_pending or 1) - 1)
    db.commit()
    return {"success": True, "message": f"Continued — {saved} new opportunities", "run_id": run_id}


def save_session_for_run(db: Session, run_id: int) -> dict:
    run = db.query(PortalRun).filter(PortalRun.id == run_id).first()
    if not run:
        return {"success": False, "message": "Run not found"}
    account = db.query(PortalAccount).filter(PortalAccount.id == run.portal_account_id).first()
    if not account:
        return {"success": False, "message": "Account not found"}

    result = browser.save_storage_state(run_id, account.id)
    if not result.get("success"):
        return result

    path = result.get("path")
    sess = _latest_session(db, account.id) or PortalSession(portal_account_id=account.id)
    if not sess.id:
        db.add(sess)
    sess.session_storage_ref = path
    sess.cookie_storage_ref = path
    sess.session_status = "active"
    sess.last_used_at = datetime.utcnow()
    sess.expires_guess_at = datetime.utcnow() + timedelta(days=14)
    account.auth_status = "connected"
    portal = db.query(Portal).filter(Portal.id == account.portal_id).first()
    if portal:
        portal.session_status = "connected"
    db.commit()
    return {"success": True, "message": "Session saved", "storage_path": path}


def cleanup_session(db: Session, portal_id: int) -> dict:
    portal = db.query(Portal).filter(Portal.id == portal_id).first()
    if not portal:
        return {"success": False, "message": "Portal not found"}
    account = db.query(PortalAccount).filter(PortalAccount.portal_id == portal_id).first()
    if not account:
        return {"success": True, "message": "No account to clean"}

    path = browser.session_storage_path(account.id)
    if path.is_file():
        path.unlink(missing_ok=True)
    for sess in db.query(PortalSession).filter(PortalSession.portal_account_id == account.id).all():
        db.delete(sess)
    account.auth_status = "not_connected"
    portal.session_status = "not_connected"
    db.commit()
    return {"success": True, "message": "Session deleted"}


def get_run(db: Session, run_id: int) -> dict | None:
    run = db.query(PortalRun).filter(PortalRun.id == run_id).first()
    if not run:
        return None
    cp = None
    if run.checkpoint_id:
        cp = db.query(PortalCheckpoint).filter(PortalCheckpoint.id == run.checkpoint_id).first()
    return _run_to_dict(run, cp)


def list_opportunities(db: Session, portal_id: int) -> list[dict]:
    account = db.query(PortalAccount).filter(PortalAccount.portal_id == portal_id).first()
    if not account:
        return []
    rows = (
        db.query(PortalOpportunity)
        .filter(PortalOpportunity.portal_account_id == account.id)
        .order_by(PortalOpportunity.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "portal_url": r.portal_url,
            "application_url": r.application_url,
            "deadline": r.deadline,
            "award_amount": r.award_amount,
            "status_in_portal": r.status_in_portal,
            "portal_run_id": r.portal_run_id,
        }
        for r in rows
    ]


# Backward compatibility
def open_portal_session(db: Session, portal_id: int) -> dict:
    return start_browser_session(db, portal_id)


def save_session_stub(db: Session, portal_account_id: int, storage_note: str = "manual_session") -> dict:
    account = db.query(PortalAccount).filter(PortalAccount.id == portal_account_id).first()
    if not account:
        return {"success": False, "message": "Account not found"}
    runs = (
        db.query(PortalRun)
        .filter(PortalRun.portal_account_id == portal_account_id)
        .order_by(PortalRun.started_at.desc())
        .first()
    )
    if runs:
        return save_session_for_run(db, runs.id)
    return {
        "success": False,
        "message": (
            "Session cannot be captured from your external browser yet. "
            "Start a browser session first, then save session."
        ),
    }
