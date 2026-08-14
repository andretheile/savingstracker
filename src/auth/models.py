"""Google identities and pending household invites."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base, TimestampMixin, UUIDMixin, UUIDType


class AuthIdentity(UUIDMixin, TimestampMixin, Base):
    """A Google account attached to a household User."""

    __tablename__ = "auth_identities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    picture: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class HouseholdInvite(UUIDMixin, TimestampMixin, Base):
    """Invite an email to share an existing household dashboard."""

    __tablename__ = "household_invites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    invited_by_email: Mapped[str] = mapped_column(String(255), nullable=False)
