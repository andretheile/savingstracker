"""KPI service — Aggregates transaction data and evaluates KPI definitions into snapshots."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.classification.models import Category
from src.classification.service import is_cashflow_relevant
from src.kpis.builtin_kpis import BUILTIN_KPIS
from src.kpis.engine import TransactionAggregates, kpi_engine
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
    stmt_acc = select(Account).where(
        Account.user_id == user_id,
        Account.is_active.is_(True),
        Account.include_in_household.is_(True),
    )
    household = list((await session.execute(stmt_acc)).scalars().all())
    account_ids = [acc.id for acc in household]
    household_ibans = {(acc.iban or "").replace(" ", "").upper() for acc in household if acc.iban}

    if not account_ids:
        return TransactionAggregates()

    # Query period transactions
    stmt_tx = (
        select(Transaction, Category)
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
    tx_count = 0
    max_expense = 0.0
    cat_totals: dict[str, float] = {}
    cat_counts: dict[str, int] = {}

    for tx, cat in rows:
        if not is_cashflow_relevant(tx, cat, household_ibans):
            continue
        amt = float(tx.amount)
        cat_name = cat.name if cat else None
        cat_key = (cat_name or "uncategorized").lower().replace(" ", "_").replace("&", "and")
        tx_count += 1

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

    first_of_period = period_start.replace(day=1)
    prev_end = first_of_period
    prev_start = (first_of_period - timedelta(days=1)).replace(day=1)

    stmt_prev = (
        select(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date < prev_end,
        )
    )
    result_prev = await session.execute(stmt_prev)
    prev_income = 0.0
    prev_expense = 0.0
    for tx, cat in result_prev.all():
        if not is_cashflow_relevant(tx, cat, household_ibans):
            continue
        amt = float(tx.amount)
        if amt > 0:
            prev_income += amt
        else:
            prev_expense += abs(amt)

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
    now = datetime.now(UTC)

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
        snapshot.kpi_definition = kpi
        session.add(snapshot)
        snapshots.append(snapshot)

    await session.flush()
    return snapshots
