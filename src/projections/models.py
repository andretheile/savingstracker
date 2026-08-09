"""Projection domain — ProjectionConfig and ProjectionSnapshot models."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin


class ProjectionConfig(UUIDMixin, TimestampMixin, Base):
    """User's savings projection configuration (benchmark, horizon, etc.)."""

    __tablename__ = "projection_configs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, default="My Savings Goal"
    )
    annual_return_pct: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, default=7.0
    )  # MSCI World default
    inflation_pct: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, default=2.0
    )
    horizon_years: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    monthly_contribution: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )  # Override — if None, use actual savings from KPI
    use_actual_savings: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Derive monthly contribution from savings rate KPI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="projection_configs")
    snapshots = relationship(
        "ProjectionSnapshot", back_populates="projection_config", lazy="selectin"
    )


class ProjectionSnapshot(UUIDMixin, Base):
    """A monthly computed savings projection with what-if scenarios."""

    __tablename__ = "projection_snapshots"

    projection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projection_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    computed_for_month: Mapped[date] = mapped_column(Date, nullable=False)
    current_savings_rate: Mapped[float] = mapped_column(
        Numeric(precision=6, scale=2), nullable=False
    )
    monthly_contribution: Mapped[float] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )
    projected_value_nominal: Mapped[float] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False
    )
    projected_value_real: Mapped[float] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False
    )  # Inflation-adjusted
    scenarios: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # What-if analysis results
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    projection_config = relationship("ProjectionConfig", back_populates="snapshots")
