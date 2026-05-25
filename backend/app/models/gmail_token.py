from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GmailToken(Base):
    """OAuth tokens — encryption at rest TODO for production."""

    __tablename__ = "gmail_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
