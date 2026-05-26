"""Trusted scholarship platforms and blocked sources."""
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrustedPlatform(Base):
    __tablename__ = "trusted_platforms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    platform_key: Mapped[str] = mapped_column(String(80), unique=True)
    allowed_domains_json: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(50), default="active")
    login_required: Mapped[str] = mapped_column(String(20), default="unknown")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class BlockedSource(Base):
    __tablename__ = "blocked_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="blocked")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
