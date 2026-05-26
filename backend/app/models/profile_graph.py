from datetime import datetime
from sqlalchemy import String, Text, Float, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

# auto_approved | needs_review | conflict | rejected | user_confirmed
MEMORY_STATUSES = ("auto_approved", "needs_review", "conflict", "rejected", "user_confirmed")

SENSITIVE_NODE_TYPES = frozenset({
    "identity",
    "citizenship",
    "international_status",
    "visa_status",
    "university",
    "major",
    "education",
    "GPA",
    "financial_need",
    "award",
})


class ProfileGraphNode(Base):
    __tablename__ = "profile_graph_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    node_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(50), default="needs_review")
    approved_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    canonical_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conflict_flag: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    used_in_essays_count: Mapped[int] = mapped_column(Integer, default=0)
    legacy_story_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
