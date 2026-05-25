"""Gmail OAuth and scholarship-focused scan — read-only MVP."""
from datetime import datetime
from urllib.parse import urlencode
import httpx
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.gmail_token import GmailToken
from app.models.scholarship import Scholarship

SCHOLARSHIP_QUERY = (
    "(scholarship OR \"financial aid\" OR grant OR fellowship OR "
    "\"engineering scholarship\" OR \"international student\" OR "
    "\"application deadline\" OR \"award opportunity\")"
)

SEARCH_TERMS = [
    "scholarship", "financial aid", "grant", "fellowship",
    "engineering scholarship", "international student scholarship",
    "application deadline", "award opportunity",
]


def gmail_status(db: Session) -> dict:
    settings = get_settings()
    if not settings.gmail_configured:
        return {
            "configured": False,
            "connected": False,
            "status": "not_configured",
            "message": "Gmail not configured — set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET",
        }
    token = db.query(GmailToken).filter(GmailToken.id == 1).first()
    if token and token.access_token:
        return {
            "configured": True,
            "connected": True,
            "status": "connected",
            "message": f"Connected as {token.email_address or 'Gmail account'}",
            "email": token.email_address,
        }
    return {
        "configured": True,
        "connected": False,
        "status": "needs_auth",
        "message": "OAuth configured — connect via auth URL",
    }


def get_auth_url() -> dict:
    settings = get_settings()
    if not settings.gmail_configured:
        return {"configured": False, "auth_url": None, "message": "Gmail not configured"}
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": settings.gmail_scopes,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"configured": True, "auth_url": url, "message": "Open URL to authorize read-only Gmail access"}


def save_tokens_from_code(db: Session, code: str) -> dict:
    settings = get_settings()
    if not settings.gmail_configured:
        return {"success": False, "message": "Gmail not configured"}

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=settings.gmail_scopes.split(),
            redirect_uri=settings.google_redirect_uri,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        token = db.query(GmailToken).filter(GmailToken.id == 1).first()
        if not token:
            token = GmailToken(id=1)
            db.add(token)
        token.access_token = creds.token
        token.refresh_token = creds.refresh_token
        token.token_uri = creds.token_uri
        token.client_id = settings.google_client_id
        token.scopes = settings.gmail_scopes
        token.expiry = creds.expiry
        token.updated_at = datetime.utcnow()
        db.commit()
        return {"success": True, "message": "Gmail connected — token stored (encryption TODO)"}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def scan_gmail(db: Session) -> dict:
    settings = get_settings()
    if not settings.gmail_configured:
        return {"configured": False, "found": 0, "message": "Gmail not configured", "scholarships": []}

    token = db.query(GmailToken).filter(GmailToken.id == 1).first()
    if not token or not token.access_token:
        return {"configured": True, "found": 0, "message": "Gmail not connected — authorize first", "scholarships": []}

    try:
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
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        results = service.users().messages().list(
            userId="me", q=SCHOLARSHIP_QUERY, maxResults=15
        ).execute()
        messages = results.get("messages", [])
        created = []
        for msg_ref in messages[:10]:
            msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="metadata").execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "Scholarship email")
            existing = db.query(Scholarship).filter(
                Scholarship.name == subject, Scholarship.source_type == "gmail"
            ).first()
            if existing:
                continue
            sch = Scholarship(
                name=f"[Gmail] {subject[:200]}",
                source_type="gmail",
                source_url=f"https://mail.google.com/mail/u/0/#inbox/{msg_ref['id']}",
                eligibility_notes=headers.get("From", ""),
                status="found",
                next_action="Review email and evaluate eligibility",
            )
            db.add(sch)
            created.append(sch)
        db.commit()
        return {
            "configured": True,
            "found": len(created),
            "message": f"Scan complete — {len(created)} new opportunities",
            "scholarships": [{"id": s.id, "name": s.name} for s in created],
        }
    except Exception as e:
        return {"configured": True, "found": 0, "message": f"Scan failed: {e}", "scholarships": []}
