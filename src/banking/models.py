"""Bank connection domain — SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin, UUIDType


class BankConnection(UUIDMixin, TimestampMixin, Base):
    """A configured connection to a bank via FinTS or other adapter."""

    __tablename__ = "bank_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_blz: Mapped[str] = mapped_column(String(16), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    fints_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    login_name: Mapped[str] = mapped_column(
        String(512), nullable=False
    )  # Encrypted at application layer
    pin_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="fints"
    )  # fints | csv

    # Sync state
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="idle"
    )  # idle | syncing | error
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bank_connections")
    transactions = relationship("Transaction", back_populates="bank_connection", lazy="selectin")
