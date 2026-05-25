from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Essay(Base):
    __tablename__ = "essays"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scholarship_id: Mapped[int | None] = mapped_column(ForeignKey("scholarships.id"), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_alignment_score: Mapped[float] = mapped_column(Float, default=0.0)
    authenticity_score: Mapped[float] = mapped_column(Float, default=0.0)
    missing_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    unsupported_claims: Mapped[list | None] = mapped_column(JSON, nullable=True)
    generic_language_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    review_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
