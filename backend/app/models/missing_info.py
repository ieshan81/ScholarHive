from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MissingInfoRequest(Base):
    __tablename__ = "missing_info_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scholarship_id: Mapped[int | None] = mapped_column(ForeignKey("scholarships.id"), nullable=True)
    essay_id: Mapped[int | None] = mapped_column(ForeignKey("essays.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    telegram_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
