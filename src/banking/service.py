"""Banking service — Bank connection orchestration and sync pipeline."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.accounts.service import create_account
from src.banking.adapters.base import AuthResult
from src.banking.adapters.fints_adapter import FinTSAdapter
from src.banking.models import BankConnection
from src.core.cache import rate_limit_check
from src.core.security import decrypt_field, encrypt_field
from src.transactions.service import add_transaction

logger = logging.getLogger(__name__)


async def create_bank_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_blz: str,
    bank_name: str,
    fints_url: str,
    login_name: str,
    adapter_type: str = "fints",
) -> BankConnection:
    """Register a new bank connection with encrypted login credentials."""
    conn = BankConnection(
        user_id=user_id,
        bank_blz=bank_blz,
        bank_name=bank_name,
        fints_url=fints_url,
        login_name=encrypt_field(login_name),
        adapter_type=adapter_type,
    )
    session.add(conn)
    await session.flush()
    return conn


async def sync_bank_connection(
    session: AsyncSession,
    connection_id: uuid.UUID,
    pin: str,
    since_days: int = 90,
) -> tuple[bool, str, AuthResult | None]:
    """Execute transaction sync for a bank connection.

    Enforces rate limiting (max 1 sync per connection per hour).
    """
    stmt = select(BankConnection).where(BankConnection.id == connection_id)
    result = await session.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn or not conn.is_active:
        return False, "Bank connection not found or inactive.", None

    # Rate limiting check
    rate_key = f"rate_limit:bank_sync:{connection_id}"
    if not await rate_limit_check(rate_key, max_calls=1, window_seconds=3600):
        return False, "Rate limit reached. Please wait an hour between bank syncs.", None

    login_name = decrypt_field(conn.login_name)
    adapter = FinTSAdapter()

    # 1. Connect & authenticate
    auth_res = await adapter.connect(conn.bank_blz, conn.fints_url, login_name, pin)
    if not auth_res.success:
        conn.sync_status = "error"
        conn.last_error = auth_res.error
        await session.flush()
        return False, f"Authentication failed: {auth_res.error}", auth_res

    if auth_res.requires_tan:
        # User must complete TAN challenge
        return True, "TAN required.", auth_res

    # 2. Complete fetch if no TAN required immediately
    await _execute_import(session, conn, adapter, auth_res.session_data, since_days)
    return True, "Sync completed successfully.", auth_res


async def complete_tan_sync(
    session: AsyncSession,
    connection_id: uuid.UUID,
    session_data: dict,
    tan: str,
    since_days: int = 90,
) -> tuple[bool, str]:
    """Submit TAN response and finish transaction import."""
    stmt = select(BankConnection).where(BankConnection.id == connection_id)
    result = await session.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        return False, "Bank connection not found."

    adapter = FinTSAdapter()
    tan_res = await adapter.handle_tan(session_data, tan)
    if not tan_res.success:
        conn.sync_status = "error"
        conn.last_error = tan_res.error
        await session.flush()
        return False, f"TAN verification failed: {tan_res.error}"

    await _execute_import(session, conn, adapter, session_data, since_days)
    return True, "Sync completed successfully after TAN."


async def _execute_import(
    session: AsyncSession,
    conn: BankConnection,
    adapter: FinTSAdapter,
    session_data: dict,
    since_days: int,
) -> None:
    """Internal helper to pull accounts & transactions from connected adapter."""
    try:
        conn.sync_status = "syncing"
        await session.flush()

        accounts = await adapter.fetch_accounts(session_data)
        since_date = date.today() - timedelta(days=since_days)

        for b_acc in accounts:
            # Match existing user account by IBAN or create new one
            stmt_acc = select(Account).where(
                Account.user_id == conn.user_id,
                Account.iban == b_acc.iban,
            )
            res_acc = await session.execute(stmt_acc)
            acc = res_acc.scalar_one_or_none()

            if not acc and b_acc.iban:
                acc = await create_account(
                    session=session,
                    user_id=conn.user_id,
                    name=f"{conn.bank_name} ({b_acc.iban[-4:]})",
                    iban=b_acc.iban,
                    currency=b_acc.currency,
                )

            if not acc:
                continue

            # Fetch & import transactions
            raw_txs = await adapter.fetch_transactions(session_data, b_acc.iban, since_date)
            for r_tx in raw_txs:
                try:
                    await add_transaction(
                        session=session,
                        user_id=conn.user_id,
                        account_id=acc.id,
                        tx_date=r_tx.transaction_date,
                        amount=r_tx.amount,
                        description=r_tx.description,
                        counterparty=r_tx.counterparty,
                        reference=r_tx.reference,
                        bank_connection_id=conn.id,
                        auto_classify=True,
                    )
                except ValueError:
                    # Duplicate skipped
                    pass

        conn.sync_status = "idle"
        conn.last_synced_at = datetime.now(timezone.utc)
        conn.last_error = None
        await session.flush()

    finally:
        await adapter.disconnect(session_data)
