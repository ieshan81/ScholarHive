# ScholarHive AI

Private scholarship operating system for one international Mechanical Engineering student in the United States. Finds opportunities, scans Gmail (read-only), stores your profile and stories, scores eligibility, drafts essays with Gemini, asks missing questions via Telegram, and prepares applications for **human review only**.

> **Note:** The workspace was empty at build time — this MVP includes a full dark academic-tech UI and FastAPI backend scaffold. No existing UI files were overwritten.

## Safety rules

- No automatic application submission without human approval
- No CAPTCHA bypass
- No AI-detector evasion — use **Personal Voice Review** / **Authenticity Review**
- No fabricated facts in essays
- Unknown profile data → Telegram question or `missing_info` status
- Portal login / CAPTCHA / signature → `manual_step_needed`

## Architecture

| Layer | Stack |
|-------|--------|
| Frontend | React 18 + Vite + Tailwind (port 5173) |
| Backend | FastAPI + SQLAlchemy (port 8000) |
| Database | PostgreSQL (Railway) or SQLite (local) |
| AI | Gemini API (essays, structuring search results) |
| Web search | Tavily API (scholarship discovery — manual UI trigger) |
| Email | Gmail OAuth (read-only, optional) |
| Messaging | Telegram Bot API (optional) |

## Local setup

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
# Edit ..\.env if needed — SQLite works with no extra setup
cd ..
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

Health: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — API proxied to backend.

### 3. Optional PostgreSQL

```powershell
docker compose up -d
# Set DATABASE_URL=postgresql://scholarhive:local@localhost:5432/scholarhive
```

### 4. Run tests

```powershell
.\scripts\verify.ps1
```

Or:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./test_scholarhive.db"
pytest tests/ -v
```

## Environment variables (Railway)

**Set on Railway today:**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `SECRET_KEY` | Long random secret |
| `ENVIRONMENT` | `production` |
| `GEMINI_API_KEY` | Essay drafts + structuring Tavily results |
| `TAVILY_API_KEY` | Web scholarship search (manual from UI) |

**Future optional:**

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLIENT_ID` | Gmail OAuth |
| `GOOGLE_CLIENT_SECRET` | Gmail OAuth |
| `TELEGRAM_BOT_TOKEN` | Missing-info questions |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook validation |

**Remove from Railway if present (now code defaults):**

`APP_BASE_URL`, `BACKEND_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, `RAILWAY_PUBLIC_DOMAIN`, `LOG_LEVEL`, `GMAIL_SCOPES`, `GOOGLE_REDIRECT_URI`, `SERPAPI_API_KEY`, `UPLOAD_STORAGE_DRIVER`, `UPLOAD_STORAGE_PATH`, `MAX_UPLOAD_MB`, `ENABLE_DEMO_DATA`

**Code defaults (production):**

- Public URL: `https://web-production-586ef.up.railway.app`
- Gmail redirect: `https://web-production-586ef.up.railway.app/api/gmail/callback`
- Gmail scope: `https://www.googleapis.com/auth/gmail.readonly`
- Demo data: **disabled** in production
- Upload path: `/data/uploads` (mount Railway volume at `/data` for persistence)
- SerpAPI: **not used** — Tavily only

Copy `.env.example` for local dev. Never commit secrets.

## Web scholarship search (Tavily)

- Manual only — use **Web Search** in the UI or `POST /api/web-search/run`
- Does not run on startup
- Requires `TAVILY_API_KEY` + recommended `GEMINI_API_KEY` for structured extraction
- Deduplicates by URL/name, filters low-trust/spam, never overwrites user-edited scholarships
- SerpAPI is not used

## Personal Voice Review

- Not a “humanizer” and not AI-detector evasion
- Flags generic/robotic wording, vague claims, missing evidence
- Rewrite modes use only Profile Vault + Story Bank facts (no fabrication)

## API overview

- `GET /health` — service + integration status
- `GET /api/web-search/status`, `POST /api/web-search/run`
- Profile: `GET/PUT /api/profile`
- Stories: `GET/POST/PUT/DELETE /api/stories`
- Scholarships: `GET/POST`, evaluate, move-status, apply-prep
- Essays: generate, review (Authenticity), approve
- Gmail: status, auth-url, callback, scan
- Telegram: status, webhook, send-test, send-question
- Missing info, documents, dashboard, settings, manual jobs

## Gmail OAuth setup

1. Google Cloud Console → APIs → enable Gmail API
2. OAuth consent screen (external/test user: you)
3. Credentials → OAuth client (Web)
4. Redirect URI: `https://YOUR-BACKEND/api/gmail/callback` (and local `http://localhost:8000/api/gmail/callback`)
5. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GMAIL_SCOPES`

## Telegram bot setup

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy token → `TELEGRAM_BOT_TOKEN`
2. Set `TELEGRAM_WEBHOOK_SECRET` (random string)
3. After deploy: `POST https://api.telegram.org/bot<TOKEN>/setWebhook` with  
   `url=https://YOUR-BACKEND/api/telegram/webhook` and header `X-Telegram-Bot-Api-Secret-Token: <SECRET>`
4. Get your chat ID (e.g. [@userinfobot](https://t.me/userinfobot)) for test messages in UI

## Gemini setup

1. [Google AI Studio](https://aistudio.google.com/) → API key → `GEMINI_API_KEY`
2. Essay Studio → generate draft (only when key is set)

## Railway deployment

### One service vs two?

**Recommended for MVP: ONE Railway service**

- Build: frontend `npm run build` + backend `pip install` (see `nixpacks.toml`)
- Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- FastAPI serves `frontend/dist` at `/` when present
- Add **Railway Postgres** plugin; link `DATABASE_URL` to the service

**Alternative: TWO services** (frontend static host + API service) if you prefer separate scaling — set `VITE_API_URL` to backend URL at frontend build time.

### Connect Railway Postgres

1. Railway project → **+ New** → **Database** → **PostgreSQL**
2. Copy `DATABASE_URL` from Postgres service variables
3. Add to **app service** variables (or use Railway variable reference `${{Postgres.DATABASE_URL}}`)

### Build command (Nixpacks — `nixpacks.toml`)

```
cd backend && pip install -r requirements.txt
cd frontend && npm ci && npm run build
```

`frontend/dist` is built on Railway (not committed). FastAPI serves it from `ScholarHive/frontend/dist` when present.

### Start command

```
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

(Also in `Procfile`, `nixpacks.toml`, and `railway.json`.)

### Health check

- Path: `/health`
- Expected: `"status": "ok"`, `"service": "ScholarHive AI"`

### After deploy (integrations not configured)

| Integration | What you'll see | What to do |
|-------------|-----------------|------------|
| Gemini | Settings + Essay Studio warning | Add `GEMINI_API_KEY`, redeploy |
| Gmail | "Gmail not configured" | Add Google OAuth vars, set redirect in Google Cloud |
| Telegram | Webhook ignored safely | Add token + secret, set webhook URL |
| Database | `not_connected` in health | Fix `DATABASE_URL` |

App **still runs** without optional keys — use manual triggers and edit profile/stories locally.

## MVP limitations

- No CAPTCHA bypass
- No unsupervised auto-submission
- No fake facts in essays (Gemini instructed; you must verify)
- No AI-detector evasion tooling
- No production demo/mock data
- Gmail tokens stored without encryption at rest (TODO)
- Document vault metadata-only unless Railway volume mounted at `/data`
- Background jobs: manual UI buttons only (no cron)
- Single-user (no auth/multi-tenant)

## Railway volume (uploads)

For persistent document uploads later, create a Railway volume and mount it at `/data`. Without a volume, uploads may not survive redeploys.

## Next phase roadmap

- Encrypt OAuth tokens at rest
- S3/R2 document uploads
- Scheduled Gmail/eligibility jobs (Railway cron or worker)
- Richer scholarship web scraping (with ToS compliance)
- Optional login for multi-device access

---

## Manual Railway checklist

1. Create Railway project  
2. Connect GitHub repository  
3. Add Railway Postgres  
4. Copy Railway Postgres `DATABASE_URL` into app env (if not auto-injected)  
5. Add `GEMINI_API_KEY`  
6. Add `GOOGLE_CLIENT_ID`  
7. Add `GOOGLE_CLIENT_SECRET`  
8. Add `GOOGLE_REDIRECT_URI` = `https://<your-backend>/api/gmail/callback`  
9. Add `GMAIL_SCOPES` = `https://www.googleapis.com/auth/gmail.readonly`  
10. Add `TELEGRAM_BOT_TOKEN`  
11. Add `TELEGRAM_WEBHOOK_SECRET`  
12. Add `APP_BASE_URL` = public URL  
13. Add `FRONTEND_URL` = same or separate frontend URL  
14. Add `BACKEND_URL` = API public URL  
15. Add `SECRET_KEY` (long random string)  
16. Set `ENVIRONMENT=production`  
17. Confirm start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
18. Deploy  
19. Test `GET /health`  
20. Open app → Settings page  
21. Configure Gmail OAuth redirect in Google Cloud  
22. Configure Telegram webhook after deployment  
23. Test manual Gmail scan  
24. Test Telegram message  
25. Test essay generation if Gemini is configured  
