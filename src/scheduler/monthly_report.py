"""Monthly report builder — Generates text digests for Telegram delivery."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balance_sheets.service import generate_balance_sheet
from src.kpis.service import evaluate_and_save_kpis_for_user
from src.projections.service import generate_user_projection
from src.transactions.models import Transaction


async def build_monthly_report_payload(
    session: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> tuple[dict, str]:
    """Generate complete monthly financial data and format a Telegram markdown message."""

    # 1. Compute KPIs
    kpi_snapshots = await evaluate_and_save_kpis_for_user(session, user_id, period_start, period_end)

    # 2. Generate balance sheet
    bs = await generate_balance_sheet(session, user_id, period_start, period_end)

    # 3. Generate savings projection
    proj_data, proj_snap = await generate_user_projection(session, user_id, period_start, period_end)

    # 4. Check uncategorized transaction count
    stmt_uncat = (
        select(Transaction)
        .where(
            Transaction.category_id.is_(None),
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    )
    result_uncat = await session.execute(stmt_uncat)
    uncat_count = len(result_uncat.scalars().all())

    # Build report data dict
    month_str = period_start.strftime("%B %Y")
    data_payload = {
        "month": month_str,
        "total_income": float(bs.total_income),
        "total_expense": float(bs.total_expense),
        "net_cashflow": float(bs.net_cashflow),
        "savings_rate_pct": float(bs.savings_rate_pct),
        "uncategorized_count": uncat_count,
        "projected_real_20y": float(proj_data.baseline.real),
    }

    # Format text for Telegram
    lines = [
        f"📊 *Monthly Report — {month_str}*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Income:*     €{bs.total_income:,.2f}",
        f"💸 *Expenses:*   €{bs.total_expense:,.2f}",
        f"📈 *Net Saved:*   €{bs.net_cashflow:,.2f} ({bs.savings_rate_pct:.1f}%)",
        "",
        "📊 *Top Expenses by Category:*",
    ]

    for item in bs.expense_items[:5]:
        pct = (item.amount / bs.total_expense * 100) if bs.total_expense > 0 else 0
        lines.append(f"  • {item.icon} {item.category_name}: €{item.amount:,.2f} ({pct:.1f}%)")

    lines.extend([
        "",
        "🔮 *Savings Projection (20 Years, MSCI World 7%):*",
        f"  Current monthly savings: €{proj_data.monthly_contribution:,.2f}",
        f"  Projected real value: *€{proj_data.baseline.real:,.2f}*",
    ])

    if proj_data.scenarios:
        s = proj_data.scenarios[0]  # +5% scenario
        lines.append(f"  💡 _{s.description}:_ +€{s.delta_vs_baseline_real:,.2f} extra!")

    if uncat_count > 0:
        lines.extend([
            "",
            f"⚠️ *{uncat_count} transactions uncategorized* → type /uncategorized to review.",
        ])

    return data_payload, "\n".join(lines)
