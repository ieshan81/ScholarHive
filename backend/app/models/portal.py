from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Portal(Base):
    __tablename__ = "portals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    canonical_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain_status: Mapped[str] = mapped_column(String(50), default="active")
    portal_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portal_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    login_required: Mapped[str] = mapped_column(String(20), default="unknown")
    login_method: Mapped[str] = mapped_column(String(50), default="unknown")
    terms_status: Mapped[str] = mapped_column(String(50), default="unknown")
    session_status: Mapped[str] = mapped_column(String(50), default="not_connected")
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opportunities_discovered: Mapped[int] = mapped_column(Integer, default=0)
    applications_prepared: Mapped[int] = mapped_column(Integer, default=0)
    checkpoints_pending: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PortalAccount(Base):
    __tablename__ = "portal_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portal_id: Mapped[int | None] = mapped_column(ForeignKey("portals.id"), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portal_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_method: Mapped[str] = mapped_column(String(50), default="unknown")
    username_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_status: Mapped[str] = mapped_column(String(50), default="not_connected")
    terms_status: Mapped[str] = mapped_column(String(50), default="unknown")
    terms_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PortalSession(Base):
    __tablename__ = "portal_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portal_account_id: Mapped[int] = mapped_column(ForeignKey("portal_accounts.id"))
    session_status: Mapped[str] = mapped_column(String(50), default="needs_login")
    session_storage_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cookie_storage_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_guess_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checkpoint_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PortalCheckpoint(Base):
    __tablename__ = "portal_checkpoints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portal_account_id: Mapped[int | None] = mapped_column(ForeignKey("portal_accounts.id"), nullable=True)
    portal_session_id: Mapped[int | None] = mapped_column(ForeignKey("portal_sessions.id"), nullable=True)
    checkpoint_type: Mapped[str] = mapped_column(String(80))
    current_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    instruction_to_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PortalRun(Base):
    __tablename__ = "portal_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portal_account_id: Mapped[int | None] = mapped_column(ForeignKey("portal_accounts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    checkpoint_id: Mapped[int | None] = mapped_column(ForeignKey("portal_checkpoints.id"), nullable=True)
    current_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    forms_found: Mapped[int] = mapped_column(Integer, default=0)
    forms_prepared: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_log_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PortalOpportunity(Base):
    __tablename__ = "portal_opportunities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portal_account_id: Mapped[int | None] = mapped_column(ForeignKey("portal_accounts.id"), nullable=True)
    portal_run_id: Mapped[int | None] = mapped_column(ForeignKey("portal_runs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    provider: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portal_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    award_amount: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eligibility_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_in_portal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extracted_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    linked_scholarship_id: Mapped[int | None] = mapped_column(ForeignKey("scholarships.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApplicationFormDraft(Base):
    __tablename__ = "application_form_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scholarship_id: Mapped[int | None] = mapped_column(ForeignKey("scholarships.id"), nullable=True)
    portal_opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("portal_opportunities.id"), nullable=True)
    form_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    filled_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    essays_needed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    documents_needed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="draft_ready")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
