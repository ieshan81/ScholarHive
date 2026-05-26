from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str] = mapped_column(String(100))
    storage_url_or_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")
    processing_status: Mapped[str] = mapped_column(String(50), default="uploaded")
    source_type: Mapped[str] = mapped_column(String(80), default="other")
    status: Mapped[str] = mapped_column(String(50), default="missing")
    related_scholarship_id: Mapped[int | None] = mapped_column(
        ForeignKey("scholarships.id"), nullable=True
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
