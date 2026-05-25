from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_story: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    used_in_essays_count: Mapped[int] = mapped_column(Integer, default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
