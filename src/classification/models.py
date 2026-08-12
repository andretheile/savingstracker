"""Classification domain — Category and ClassificationRule models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin, UUIDType


class Category(UUIDMixin, TimestampMixin, Base):
    """Hierarchical transaction category (income / expense / transfer)."""

    __tablename__ = "categories"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # NULL = system default category
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(String(8), nullable=False, default="❓")
    direction: Mapped[str] = mapped_column(
        String(16), nullable=False, default="expense"
    )  # income | expense | transfer
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent", lazy="selectin")
    transactions = relationship("Transaction", back_populates="category", lazy="selectin")
    classification_rules = relationship(
        "ClassificationRule", back_populates="category", lazy="selectin"
    )


class ClassificationRule(UUIDMixin, TimestampMixin, Base):
    """Pattern-matching rule to auto-classify transactions into categories."""

    __tablename__ = "classification_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    field: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # description | counterparty | amount
    operator: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # contains | equals | regex | gt | lt
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )  # lower = higher priority
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="classification_rules")
