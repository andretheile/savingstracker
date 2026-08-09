"""Transaction domain — SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin


class Transaction(UUIDMixin, TimestampMixin, Base):
    """A single financial transaction within an account."""

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "transaction_date"),
        Index("ix_transactions_category", "category_id"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    bank_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )  # positive = income, negative = expense
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    counterparty: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    reference: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Deduplication hash: SHA256(account_id + date + amount + description)
    import_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )

    is_manually_classified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    bank_connection = relationship("BankConnection", back_populates="transactions")
