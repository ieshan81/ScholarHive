"""Gmail Scanner V2 — classify full messages before saving scholarships."""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.discovery import DiscoveryRun
from app.models.gmail_message import GmailMessage
from app.models.gmail_token import GmailToken
from app.services.discovery_classifier import classify_candidate, extract_domain
from app.services.discovery_pipeline import create_candidate, process_candidate

GMAIL_QUERY = (
    "(scholarship OR scholarships OR \"financial aid\" OR fellowship OR grant OR "
    "\"award opportunity\" OR \"STEM scholarship\" OR \"engineering scholarship\" OR "
    "\"international student\" OR \"application deadline\") "
    "-loan -refinance -\"student loan\" -marketing"
)


def _decode_body(payload: dict) -> str:
    texts: list[str] = []
    if payload.get("body", {}).get("data"):
        texts.append(base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore"))
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            texts.append(base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore"))
        elif part.get("parts"):
            texts.append(_decode_body(part))
    return "\n".join(texts)[:30000]


def _extract_links(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>\"']+", text or "")[:30]


def _get_gmail_service(db: Session):
    settings = get_settings()
    token = db.query(GmailToken).filter(GmailToken.id == 1).first()
    if not token or not token.access_token:
        return None, None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri=token.token_uri or "https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=settings.gmail_scopes.split(),
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False), token


def fetch_message_detail(service, msg_id: str) -> dict:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body = _decode_body(msg.get("payload", {}))
    return {
        "gmail_id": msg_id,
        "subject": headers.get("Subject", ""),
        "sender": headers.get("From", ""),
        "snippet": msg.get("snippet", ""),
        "body_text": body,
        "links": _extract_links(body),
        "received_at": headers.get("Date"),
    }


async def scan_gmail_v2(db: Session, days: int = 30, max_messages: int = 25) -> dict:
    settings = get_settings()
    if not settings.gmail_configured:
        return {"configured": False, "message": "Gmail not configured"}

    service, token = _get_gmail_service(db)
    if not service:
        return {"configured": True, "connected": False, "message": "Gmail not connected"}

    q = f"{GMAIL_QUERY} newer_than:{days}d"
    run = DiscoveryRun(source_type="gmail", query_or_label=q, status="running")
    db.add(run)
    db.commit()

    results = service.users().messages().list(userId="me", q=q, maxResults=max_messages).execute()
    messages = results.get("messages", [])
    saved = dup = rejected = scanned = 0
    errors: list[str] = []

    for msg_ref in messages:
        try:
            detail = fetch_message_detail(service, msg_ref["id"])
            scanned += 1
            existing = db.query(GmailMessage).filter(GmailMessage.gmail_id == detail["gmail_id"]).first()
            if existing:
                continue

            classification, conf, reason = classify_candidate(
                detail["subject"],
                f"{detail['snippet']} {detail['body_text'][:2000]}",
                "gmail",
                detail["sender"],
            )
            gm = GmailMessage(
                gmail_id=detail["gmail_id"],
                subject=detail["subject"],
                sender=detail["sender"],
                snippet=detail["snippet"],
                body_text=detail["body_text"],
                links_json=json.dumps(detail["links"]),
                domain=extract_domain(detail["links"][0]) if detail["links"] else extract_domain(detail["sender"]),
                classification=classification,
                classification_reason=reason,
                status="scanned",
            )
            db.add(gm)
            db.flush()

            cand = create_candidate(
                db,
                run.id,
                "gmail",
                detail["subject"] or "(no subject)",
                detail["links"][0] if detail["links"] else f"https://mail.google.com/mail/u/0/#inbox/{detail['gmail_id']}",
                snippet=detail["snippet"],
                sender=detail["sender"],
                raw_content=detail["body_text"],
                gmail_message_id=detail["gmail_id"],
            )
            gm.discovery_candidate_id = cand.id
            ps = await process_candidate(db, cand, f"gmail:{detail['subject'][:80]}")
            saved += ps.get("saved", 0)
            dup += ps.get("duplicate", 0)
            rejected += ps.get("rejected", 0) + ps.get("source_page_only", 0)
            if classification in ("irrelevant", "spam", "loan", "marketing"):
                gm.status = "rejected"
            elif ps.get("saved"):
                gm.status = "opportunity_saved"
        except Exception as e:
            errors.append(str(e))

    run.total_candidates = scanned
    run.opportunities_saved = saved
    run.duplicates_skipped = dup
    run.rejected_count = rejected
    run.status = "completed"
    run.finished_at = datetime.utcnow()
    run.errors = "\n".join(errors) if errors else None
    db.commit()

    return {
        "configured": True,
        "connected": True,
        "message": f"Gmail scan: {scanned} messages reviewed, {saved} scholarships saved, {rejected} rejected",
        "scanned": scanned,
        "saved": saved,
        "duplicates_skipped": dup,
        "rejected_count": rejected,
        "errors": errors,
    }


def list_gmail_messages(db: Session, status: str | None = None) -> list[dict]:
    q = db.query(GmailMessage).order_by(GmailMessage.created_at.desc())
    if status:
        q = q.filter(GmailMessage.status == status)
    rows = q.limit(100).all()
    return [
        {
            "id": r.id,
            "gmail_id": r.gmail_id,
            "subject": r.subject,
            "sender": r.sender,
            "snippet": r.snippet,
            "body_text": r.body_text,
            "links": json.loads(r.links_json or "[]"),
            "domain": r.domain,
            "classification": r.classification,
            "classification_reason": r.classification_reason,
            "status": r.status,
            "discovery_candidate_id": r.discovery_candidate_id,
            "gmail_url": f"https://mail.google.com/mail/u/0/#inbox/{r.gmail_id}",
        }
        for r in rows
    ]
