"""Account domain — SQLAlchemy model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin


class Account(UUIDMixin, TimestampMixin, Base):
    """A bank account belonging to a user."""

    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    initial_balance: Mapped[float] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False, default=0
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", lazy="selectin")
