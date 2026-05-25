import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Serve built frontend in production (Railway single-service deploy)
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
