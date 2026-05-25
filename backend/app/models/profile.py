from datetime import datetime
from sqlalchemy import String, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    personal_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    major: Mapped[str | None] = mapped_column(String(255), nullable=True)
    international_student: Mapped[bool] = mapped_column(Boolean, default=True)
    visa_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    financial_need: Mapped[str | None] = mapped_column(Text, nullable=True)
    projects: Mapped[str | None] = mapped_column(Text, nullable=True)
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    leadership: Mapped[str | None] = mapped_column(Text, nullable=True)
    volunteering: Mapped[str | None] = mapped_column(Text, nullable=True)
    career_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_statements: Mapped[str | None] = mapped_column(Text, nullable=True)
    scholarship_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
