from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.config import get_settings
from app.database import engine, Base, SessionLocal
from app.seed import seed_database
from app.routers import (
    health,
    profile,
    stories,
    scholarships,
    essays,
    gmail,
    telegram,
    missing_info,
    documents,
    dashboard,
    jobs,
)
from app.routers import settings as settings_router

app_settings = get_settings()

# Railway build output: ScholarHive/frontend/dist (relative to backend/app/main.py)
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="ScholarHive AI",
    description="Private scholarship operating system — one-user MVP",
    version="0.1.0",
    lifespan=lifespan,
)

origins = app_settings.cors_origin_list
if app_settings.environment == "development":
    origins = list(set(origins + ["http://localhost:5173", "http://127.0.0.1:5173"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API and health routes first (must not be swallowed by SPA fallback)
app.include_router(health.router)
app.include_router(profile.router)
app.include_router(stories.router)
app.include_router(scholarships.router)
app.include_router(essays.router)
app.include_router(gmail.router)
app.include_router(telegram.router)
app.include_router(missing_info.router)
app.include_router(documents.router)
app.include_router(dashboard.router)
app.include_router(settings_router.router)
app.include_router(jobs.router)


def _register_frontend() -> None:
    """Serve Vite build with SPA fallback for client-side routes."""
    if not FRONTEND_DIST.is_dir():
        return

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa_fallback(request: Request, full_path: str = ""):
        path = full_path.strip("/")

        # Unknown API paths → JSON 404 (do not return HTML)
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # /health is registered on the health router; fallback only if missing
        if path == "health":
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # Serve real static files from dist (favicon, etc.)
        if path:
            static_file = (FRONTEND_DIST / path).resolve()
            try:
                static_file.relative_to(FRONTEND_DIST.resolve())
            except ValueError:
                pass
            else:
                if static_file.is_file():
                    return FileResponse(static_file)

        if INDEX_HTML.is_file():
            return FileResponse(INDEX_HTML)

        return JSONResponse({"detail": "Not Found"}, status_code=404)


_register_frontend()
