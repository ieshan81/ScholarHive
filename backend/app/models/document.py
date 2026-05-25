from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(100))
    storage_url_or_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="missing")
    related_scholarship_id: Mapped[int | None] = mapped_column(
        ForeignKey("scholarships.id"), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
