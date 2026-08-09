"""KPI service — Aggregates transaction data and evaluates KPI definitions into snapshots."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.classification.models import Category
from src.kpis.builtin_kpis import BUILTIN_KPIS
from src.kpis.engine import KPIEngine, TransactionAggregates, kpi_engine
from src.kpis.models import KPIDefinition, KPISnapshot
from src.transactions.models import Transaction


async def ensure_builtin_kpis_seeded(session: AsyncSession) -> None:
    """Ensure system built-in KPI definitions exist in the database."""
    stmt = select(KPIDefinition).where(KPIDefinition.user_id.is_(None))
    result = await session.execute(stmt)
    existing_names = {k.name for k in result.scalars().all()}

    for b in BUILTIN_KPIS:
        if b.name not in existing_names:
            kpi = KPIDefinition(
                user_id=None,
                name=b.name,
                description=b.description,
                formula=b.formula,
                unit=b.unit,
                period=b.period,
            )
            session.add(kpi)
    await session.flush()


async def compute_aggregates_for_period(
    session: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> TransactionAggregates:
    """Fetch transaction data for a user and construct TransactionAggregates."""
    # Find all accounts for user
    stmt_acc = select(Account.id).where(Account.user_id == user_id)
    result_acc = await session.execute(stmt_acc)
    account_ids = result_acc.scalars().all()

    if not account_ids:
        return TransactionAggregates()

    # Query period transactions
    stmt_tx = (
        select(Transaction, Category.name)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    )
    result_tx = await session.execute(stmt_tx)
    rows = result_tx.all()

    total_income = 0.0
    total_expense = 0.0
    tx_count = len(rows)
    max_expense = 0.0
    cat_totals: dict[str, float] = {}
    cat_counts: dict[str, int] = {}

    for tx, cat_name in rows:
        amt = float(tx.amount)
        cat_key = (cat_name or "uncategorized").lower().replace(" ", "_").replace("&", "and")

        if amt > 0:
            total_income += amt
        else:
            exp = abs(amt)
            total_expense += exp
            if exp > max_expense:
                max_expense = exp

            cat_totals[cat_key] = cat_totals.get(cat_key, 0.0) + exp
            cat_counts[cat_key] = cat_counts.get(cat_key, 0) + 1

    net_cashflow = total_income - total_expense
    avg_expense = (total_expense / tx_count) if tx_count > 0 else 0.0
    days_in_period = max(1, (period_end - period_start).days + 1)

    # Compute previous period for MoM comparison
    period_len = (period_end - period_start).days + 1
    prev_start = period_start.replace(month=period_start.month - 1) if period_start.month > 1 else period_start.replace(year=period_start.year - 1, month=12)
    prev_end = period_start.replace(day=1)

    stmt_prev = select(Transaction.amount).where(
        Transaction.account_id.in_(account_ids),
        Transaction.transaction_date >= prev_start,
        Transaction.transaction_date < prev_end,
    )
    result_prev = await session.execute(stmt_prev)
    prev_amts = result_prev.scalars().all()

    prev_income = sum(float(a) for a in prev_amts if a > 0)
    prev_expense = sum(abs(float(a)) for a in prev_amts if a < 0)

    return TransactionAggregates(
        total_income=total_income,
        total_expense=total_expense,
        net_cashflow=net_cashflow,
        tx_count=tx_count,
        avg_expense=avg_expense,
        max_expense=max_expense,
        days_in_period=days_in_period,
        prev_total_income=prev_income,
        prev_total_expense=prev_expense,
        prev_net_cashflow=prev_income - prev_expense,
        category_totals=cat_totals,
        category_counts=cat_counts,
    )


async def evaluate_and_save_kpis_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> Sequence[KPISnapshot]:
    """Compute all active KPIs (built-in + user defined) for a period and save snapshots."""
    await ensure_builtin_kpis_seeded(session)

    # Fetch all applicable KPIs
    stmt_defs = select(KPIDefinition).where(
        (KPIDefinition.user_id == user_id) | (KPIDefinition.user_id.is_(None)),
        KPIDefinition.is_active.is_(True),
    )
    result_defs = await session.execute(stmt_defs)
    kpi_defs = result_defs.scalars().all()

    aggregates = await compute_aggregates_for_period(session, user_id, period_start, period_end)

    snapshots = []
    now = datetime.now(timezone.utc)

    for kpi in kpi_defs:
        res = kpi_engine.compute(kpi.formula, aggregates)
        snapshot = KPISnapshot(
            kpi_id=kpi.id,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            value=res.value,
            variable_values=res.variable_values,
            computed_at=now,
        )
        session.add(snapshot)
        snapshots.append(snapshot)

    await session.flush()
    return snapshots
