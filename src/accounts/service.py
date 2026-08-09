"""Account service — Bank account CRUD and balance calculations."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.transactions.models import Transaction


async def create_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    iban: str | None = None,
    currency: str = "EUR",
    initial_balance: float = 0.0,
) -> Account:
    """Create a new bank account for a user."""
    account = Account(
        user_id=user_id,
        name=name,
        iban=iban,
        currency=currency,
        initial_balance=initial_balance,
    )
    session.add(account)
    await session.flush()
    return account


async def list_user_accounts(
    session: AsyncSession,
    user_id: uuid.UUID,
    only_active: bool = True,
) -> Sequence[Account]:
    """Retrieve accounts belonging to a user."""
    stmt = select(Account).where(Account.user_id == user_id)
    if only_active:
        stmt = stmt.where(Account.is_active.is_(True))
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_account_balance(
    session: AsyncSession,
    account_id: uuid.UUID,
) -> Decimal:
    """Compute current account balance: initial_balance + sum(transaction amount)."""
    stmt_acc = select(Account).where(Account.id == account_id)
    result_acc = await session.execute(stmt_acc)
    account = result_acc.scalar_one_or_none()
    if not account:
        return Decimal("0.00")

    stmt_tx = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.account_id == account_id
    )
    result_tx = await session.execute(stmt_tx)
    tx_sum = result_tx.scalar() or 0

    return Decimal(str(account.initial_balance)) + Decimal(str(tx_sum))
