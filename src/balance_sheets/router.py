"""FastAPI router for Balance Sheets."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.balance_sheets.service import generate_balance_sheet
from src.core.dependencies import get_db

router = APIRouter(prefix="/balance-sheets", tags=["balance-sheets"])


class LineItemResponse(BaseModel):
    category_name: str
    icon: str
    amount: Decimal


class BalanceSheetResponse(BaseModel):
    period_start: date
    period_end: date
    total_income: Decimal
    total_expense: Decimal
    net_cashflow: Decimal
    savings_rate_pct: Decimal
    income_items: list[LineItemResponse]
    expense_items: list[LineItemResponse]
    account_balances: dict[str, Decimal]


@router.get("/{user_id}", response_model=BalanceSheetResponse)
async def get_balance_sheet(
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
    db: AsyncSession = Depends(get_db),
):
    bs = await generate_balance_sheet(db, user_id, period_start, period_end)
    return BalanceSheetResponse(
        period_start=bs.period_start,
        period_end=bs.period_end,
        total_income=bs.total_income,
        total_expense=bs.total_expense,
        net_cashflow=bs.net_cashflow,
        savings_rate_pct=bs.savings_rate_pct,
        income_items=[
            LineItemResponse(category_name=i.category_name, icon=i.icon, amount=i.amount)
            for i in bs.income_items
        ],
        expense_items=[
            LineItemResponse(category_name=i.category_name, icon=i.icon, amount=i.amount)
            for i in bs.expense_items
        ],
        account_balances=bs.account_balances,
    )
