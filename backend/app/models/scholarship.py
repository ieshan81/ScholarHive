from datetime import datetime, date
from sqlalchemy import String, Text, Boolean, Integer, Float, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Scholarship(Base):
    __tablename__ = "scholarships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500))
    provider: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="manual")
    award_amount: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    eligibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_documents: Mapped[str | None] = mapped_column(Text, nullable=True)
    essay_required: Mapped[bool] = mapped_column(Boolean, default=False)
    essay_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citizenship_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    major_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_level_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gpa_requirement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    international_allowed: Mapped[str] = mapped_column(String(20), default="unknown")
    trust_score: Mapped[float] = mapped_column(Float, default=50.0)
    eligibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    effort_score: Mapped[float] = mapped_column(Float, default=50.0)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="found")
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    eligibility_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_blockers: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    search_query_used: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    portal_login_required: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manual_step_likely: Mapped[bool] = mapped_column(Boolean, default=False)
    low_trust_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(600), nullable=True)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    classification: Mapped[str | None] = mapped_column(String(80), nullable=True)
    why_saved: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    portal_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovery_candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
