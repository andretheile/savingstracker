"""Projection service — Manages projection configurations and generates monthly snapshots."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.service import get_account_balance, list_user_accounts
from src.kpis.service import compute_aggregates_for_period
from src.projections.engine import FullProjection, compute_full_projection
from src.projections.models import ProjectionConfig, ProjectionSnapshot


async def get_or_create_user_projection_config(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> ProjectionConfig:
    """Get the active projection configuration for a user, or create a default one."""
    stmt = select(ProjectionConfig).where(
        ProjectionConfig.user_id == user_id,
        ProjectionConfig.is_active.is_(True),
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config is None:
        config = ProjectionConfig(
            user_id=user_id,
            name="Retirement / Growth Fund",
            annual_return_pct=7.0,  # MSCI World default
            inflation_pct=2.0,
            horizon_years=20,
            use_actual_savings=True,
        )
        session.add(config)
        await session.flush()

    return config


async def generate_user_projection(
    session: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> tuple[FullProjection, ProjectionSnapshot]:
    """Compute current user portfolio balance, monthly net cashflow, and run compound projection."""
    config = await get_or_create_user_projection_config(session, user_id)

    # 1. Total current balance across all active accounts
    accounts = await list_user_accounts(session, user_id)
    total_balance = Decimal("0.00")
    for acc in accounts:
        total_balance += await get_account_balance(session, acc.id)

    # 2. Monthly cashflow & aggregates for the period
    agg = await compute_aggregates_for_period(session, user_id, period_start, period_end)

    monthly_savings = agg.net_cashflow
    if not config.use_actual_savings and config.monthly_contribution is not None:
        monthly_savings = float(config.monthly_contribution)

    # Savings rate %
    savings_rate = (agg.net_cashflow / agg.total_income * 100) if agg.total_income > 0 else 0.0

    # 3. Compute full projection with engine
    projection_data = compute_full_projection(
        current_balance=float(total_balance),
        monthly_contribution=monthly_savings,
        total_income=agg.total_income,
        annual_return_pct=float(config.annual_return_pct),
        inflation_pct=float(config.inflation_pct),
        horizon_years=config.horizon_years,
    )

    # Serialise scenario data for DB snapshot
    scenario_dicts = [
        {
            "label": s.label,
            "description": s.description,
            "monthly_contribution": float(s.monthly_contribution),
            "real_fv": float(s.result.real),
            "nominal_fv": float(s.result.nominal),
            "delta_vs_baseline_real": float(s.delta_vs_baseline_real),
        }
        for s in projection_data.scenarios
    ]

    snapshot = ProjectionSnapshot(
        projection_id=config.id,
        user_id=user_id,
        computed_for_month=period_start,
        current_savings_rate=savings_rate,
        monthly_contribution=monthly_savings,
        projected_value_nominal=projection_data.baseline.nominal,
        projected_value_real=projection_data.baseline.real,
        scenarios=scenario_dicts,
        computed_at=datetime.now(timezone.utc),
    )
    session.add(snapshot)
    await session.flush()

    return projection_data, snapshot
