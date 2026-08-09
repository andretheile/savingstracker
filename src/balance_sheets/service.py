"""Balance sheet service — Generates periodic financial statements (income vs expenses)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from dateutil.relativedelta import relativedelta
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.service import get_account_balance, list_user_accounts
from src.classification.models import Category
from src.transactions.models import Transaction


@dataclass
class LineItem:
    category_name: str
    icon: str
    amount: Decimal


@dataclass
class BalanceSheet:
    period_start: date
    period_end: date
    income_items: list[LineItem] = field(default_factory=list)
    expense_items: list[LineItem] = field(default_factory=list)
    total_income: Decimal = Decimal("0.00")
    total_expense: Decimal = Decimal("0.00")
    net_cashflow: Decimal = Decimal("0.00")
    savings_rate_pct: Decimal = Decimal("0.00")
    account_balances: dict[str, Decimal] = field(default_factory=dict)


async def generate_balance_sheet(
    session: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> BalanceSheet:
    """Generate a full balance sheet statement for a user across a specified date range."""
    # 1. Accounts & current running balances
    accounts = await list_user_accounts(session, user_id)
    account_balances: dict[str, Decimal] = {}
    account_ids = [acc.id for acc in accounts]

    for acc in accounts:
        account_balances[acc.name] = await get_account_balance(session, acc.id)

    if not account_ids:
        return BalanceSheet(period_start=period_start, period_end=period_end)

    # 2. Query transactions for period
    stmt = (
        select(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    income_map: dict[str, tuple[str, Decimal]] = {}
    expense_map: dict[str, tuple[str, Decimal]] = {}

    total_inc = Decimal("0.00")
    total_exp = Decimal("0.00")

    for tx, cat in rows:
        amt = Decimal(str(tx.amount))
        cat_name = cat.name if cat else "Uncategorized"
        cat_icon = cat.icon if cat else "❓"

        if amt > 0:
            total_inc += amt
            prev = income_map.get(cat_name, (cat_icon, Decimal("0.00")))[1]
            income_map[cat_name] = (cat_icon, prev + amt)
        else:
            abs_amt = abs(amt)
            total_exp += abs_amt
            prev = expense_map.get(cat_name, (cat_icon, Decimal("0.00")))[1]
            expense_map[cat_name] = (cat_icon, prev + abs_amt)

    income_items = [
        LineItem(category_name=name, icon=icon, amount=amt)
        for name, (icon, amt) in sorted(income_map.items(), key=lambda x: x[1][1], reverse=True)
    ]
    expense_items = [
        LineItem(category_name=name, icon=icon, amount=amt)
        for name, (icon, amt) in sorted(expense_map.items(), key=lambda x: x[1][1], reverse=True)
    ]

    net_cashflow = total_inc - total_exp
    savings_rate = (net_cashflow / total_inc * 100) if total_inc > 0 else Decimal("0.00")

    return BalanceSheet(
        period_start=period_start,
        period_end=period_end,
        income_items=income_items,
        expense_items=expense_items,
        total_income=total_inc,
        total_expense=total_exp,
        net_cashflow=net_cashflow,
        savings_rate_pct=savings_rate.quantize(Decimal("0.01")),
        account_balances=account_balances,
    )
