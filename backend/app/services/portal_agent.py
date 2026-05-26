"""Portal Agent — safe browser automation scaffold (no CAPTCHA/stealth bypass)."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.portal import Portal, PortalAccount, PortalSession, PortalCheckpoint, PortalRun
from app.config import get_settings


def portal_agent_status() -> dict:
    """Playwright full automation requires a worker with browser binaries."""
    return {
        "browser_agent": "scaffold",
        "playwright_available": False,
        "message": (
            "Portal Agent API is ready. Controlled Playwright sessions are stubbed on Railway single-service deploy. "
            "Use checkpoints: connect/login manually, then call save-session after login. No CAPTCHA/2FA bypass."
        ),
        "autonomy_mode_default": "maximum_safe_autonomy",
        "final_submit": "always_manual",
    }


def open_portal_session(db: Session, portal_id: int) -> dict:
    portal = db.query(Portal).filter(Portal.id == portal_id).first()
    if not portal:
        return {"success": False, "message": "Portal not found"}

    account = db.query(PortalAccount).filter(PortalAccount.portal_id == portal_id).first()
    if not account:
        account = PortalAccount(
            portal_id=portal_id,
            domain=portal.domain,
            portal_url=portal.portal_url,
            auth_status="user_login_required",
        )
        db.add(account)
        db.flush()

    checkpoint = PortalCheckpoint(
        portal_account_id=account.id,
        checkpoint_type="login_required",
        current_url=portal.portal_url,
        instruction_to_user=(
            f"Open {portal.portal_name or portal.domain} in your browser, sign in manually "
            "(Google/email). Complete CAPTCHA/2FA if prompted. Then mark checkpoint complete and save session."
        ),
        status="pending",
    )
    db.add(checkpoint)
    run = PortalRun(
        portal_account_id=account.id,
        status="human_checkpoint_required",
        checkpoint_id=checkpoint.id,
        current_url=portal.portal_url,
        audit_log_summary="Awaiting manual login — agent paused",
    )
    db.add(run)
    portal.checkpoints_pending = (portal.checkpoints_pending or 0) + 1
    db.commit()

    return {
        "success": True,
        "portal_id": portal_id,
        "checkpoint_id": checkpoint.id,
        "run_id": run.id,
        "portal_url": portal.portal_url,
        "message": checkpoint.instruction_to_user,
        "agent_status": portal_agent_status(),
    }


def save_session_stub(db: Session, portal_account_id: int, storage_note: str = "manual_session") -> dict:
    settings = get_settings()
    path = f"{settings.upload_storage_path}/portal_sessions/{portal_account_id}.json"
    session = PortalSession(
        portal_account_id=portal_account_id,
        session_status="active",
        session_storage_ref=storage_note,
        cookie_storage_ref=path,
        last_used_at=datetime.utcnow(),
    )
    db.add(session)
    account = db.query(PortalAccount).filter(PortalAccount.id == portal_account_id).first()
    if account:
        account.auth_status = "connected"
    db.commit()
    return {
        "success": True,
        "message": "Session reference saved (metadata). Mount Railway volume at /data for persistent cookie storage.",
        "storage_path": path,
    }
