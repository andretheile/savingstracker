"""User domain — SQLAlchemy model."""

from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """Application user, identified by Telegram ID."""

    __tablename__ = "users"

    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Europe/Berlin"
    )
    preferences: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    telegram_bot_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_bot_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_bot_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_allowed_user_ids: Mapped[str] = mapped_column(
        String(512), nullable=False, default=""
    )
    telegram_allowed_chat_ids: Mapped[str] = mapped_column(
        String(512), nullable=False, default=""
    )
    openrouter_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    openrouter_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    accounts = relationship("Account", back_populates="user", lazy="selectin")
    bank_connections = relationship("BankConnection", back_populates="user", lazy="selectin")
    kpi_definitions = relationship("KPIDefinition", back_populates="user", lazy="selectin")
    projection_configs = relationship("ProjectionConfig", back_populates="user", lazy="selectin")
