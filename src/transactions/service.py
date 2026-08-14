"""Transaction service — Transaction management, hashing, deduplication, and search."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.classification.service import classify_transaction
from src.transactions.models import Transaction


def generate_import_hash(
    account_id: uuid.UUID,
    tx_date: date,
    amount: Decimal | float,
    description: str,
) -> str:
    """Generate SHA256 deduplication hash for a transaction."""
    raw = f"{account_id}:{tx_date.isoformat()}:{float(amount):.2f}:{description.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def add_transaction(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    tx_date: date,
    amount: float | Decimal,
    description: str,
    counterparty: str = "",
    reference: str = "",
    category_id: uuid.UUID | None = None,
    bank_connection_id: uuid.UUID | None = None,
    auto_classify: bool = True,
) -> Transaction:
    """Add a new transaction and optionally run classification rules."""
    imp_hash = generate_import_hash(account_id, tx_date, Decimal(str(amount)), description)

    # Check for duplicate
    existing = await session.execute(
        select(Transaction).where(Transaction.import_hash == imp_hash)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Duplicate transaction detected.")

    tx = Transaction(
        account_id=account_id,
        category_id=category_id,
        bank_connection_id=bank_connection_id,
        transaction_date=tx_date,
        amount=amount,
        description=description,
        counterparty=counterparty,
        reference=reference,
        import_hash=imp_hash,
        is_manually_classified=category_id is not None,
    )
    session.add(tx)
    await session.flush()

    if auto_classify and tx.category_id is None:
        matched_category = await classify_transaction(session, tx, user_id)
        if matched_category:
            tx.category_id = matched_category
            await session.flush()

    return tx


async def list_transactions(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 500,
) -> Sequence[Transaction]:
    """Query transactions with optional filtering, scoped to a household when user_id is set."""
    from src.accounts.models import Account

    stmt = select(Transaction).options(
        selectinload(Transaction.account),
        selectinload(Transaction.category),
    )
    if user_id is not None:
        stmt = stmt.join(Account, Transaction.account_id == Account.id).where(Account.user_id == user_id)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if start_date:
        stmt = stmt.where(Transaction.transaction_date >= start_date)
    if end_date:
        stmt = stmt.where(Transaction.transaction_date <= end_date)

    stmt = stmt.order_by(Transaction.transaction_date.desc()).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
