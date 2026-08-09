"""KPI domain — KPIDefinition and KPISnapshot models."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base_model import Base, TimestampMixin, UUIDMixin


class KPIDefinition(UUIDMixin, TimestampMixin, Base):
    """A KPI metric definition with a user-definable formula."""

    __tablename__ = "kpi_definitions"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # NULL = built-in KPI
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    formula: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # e.g. "pct(net_cashflow, total_income)"
    unit: Mapped[str] = mapped_column(
        String(16), nullable=False, default="%"
    )  # %, €, ratio
    period: Mapped[str] = mapped_column(
        String(16), nullable=False, default="monthly"
    )  # monthly | weekly | yearly
    required_variables: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Auto-extracted variable names
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="kpi_definitions")
    snapshots = relationship("KPISnapshot", back_populates="kpi_definition", lazy="selectin")


class KPISnapshot(UUIDMixin, Base):
    """A computed KPI value for a specific period."""

    __tablename__ = "kpi_snapshots"

    kpi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kpi_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(precision=14, scale=4), nullable=False)
    variable_values: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Debug: inputs used for computation
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    kpi_definition = relationship("KPIDefinition", back_populates="snapshots")
