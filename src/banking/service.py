"""Banking service — Bank connection orchestration and sync pipeline."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.service import create_account, find_account_by_iban
from src.banking.adapters.base import AuthResult
from src.banking.adapters.fints_adapter import FinTSAdapter
from src.banking.models import BankConnection
from src.classification.service import reclassify_user_transactions
from src.core.cache import rate_limit_check
from src.core.security import decrypt_field, encrypt_field
from src.transactions.models import Transaction
from src.transactions.service import add_transaction

logger = logging.getLogger(__name__)

# Live FinTS clients waiting for DKB app approval (chat / /sync).
_pending_syncs: dict[str, dict[str, Any]] = {}


def import_since_date(today: date | None = None) -> date:
    """First day of the previous calendar month (July 1 when today is in August)."""
    today = today or date.today()
    return (today.replace(day=1) - timedelta(days=1)).replace(day=1)


def _encrypt_optional(value: str | None) -> str | None:
    if not value:
        return None
    return encrypt_field(value)


def connection_pin(conn: BankConnection) -> str:
    if not conn.pin_encrypted:
        return ""
    try:
        return decrypt_field(conn.pin_encrypted)
    except (ValueError, RuntimeError):
        return ""


def put_pending_sync(user_id: uuid.UUID, payload: dict[str, Any]) -> None:
    _pending_syncs[str(user_id)] = payload


def get_pending_sync(user_id: uuid.UUID) -> dict[str, Any] | None:
    return _pending_syncs.get(str(user_id))


def pop_pending_sync(user_id: uuid.UUID) -> dict[str, Any] | None:
    return _pending_syncs.pop(str(user_id), None)


def clear_pending_syncs() -> None:
    _pending_syncs.clear()


async def list_active_connections(
    session: AsyncSession, user_id: uuid.UUID
) -> list[BankConnection]:
    stmt = (
        select(BankConnection)
        .where(BankConnection.user_id == user_id, BankConnection.is_active.is_(True))
        .order_by(BankConnection.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def upsert_bank_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_blz: str,
    bank_name: str,
    fints_url: str,
    login_name: str,
    pin: str | None = None,
    adapter_type: str = "fints",
) -> BankConnection:
    """Create or update the household's FinTS connection, storing an encrypted PIN."""
    stmt = select(BankConnection).where(
        BankConnection.user_id == user_id,
        BankConnection.bank_blz == bank_blz,
        BankConnection.is_active.is_(True),
    )
    conn = (await session.execute(stmt)).scalars().first()
    if conn is None:
        conn = BankConnection(
            user_id=user_id,
            bank_blz=bank_blz,
            bank_name=bank_name,
            fints_url=fints_url,
            login_name=encrypt_field(login_name),
            pin_encrypted=_encrypt_optional(pin),
            adapter_type=adapter_type,
        )
        session.add(conn)
    else:
        conn.bank_name = bank_name or conn.bank_name
        conn.fints_url = fints_url or conn.fints_url
        conn.login_name = encrypt_field(login_name)
        if pin:
            conn.pin_encrypted = encrypt_field(pin)
    await session.flush()
    return conn


async def create_bank_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_blz: str,
    bank_name: str,
    fints_url: str,
    login_name: str,
    adapter_type: str = "fints",
    pin: str | None = None,
) -> BankConnection:
    """Register a new bank connection with encrypted login credentials."""
    return await upsert_bank_connection(
        session,
        user_id=user_id,
        bank_blz=bank_blz,
        bank_name=bank_name,
        fints_url=fints_url,
        login_name=login_name,
        pin=pin,
        adapter_type=adapter_type,
    )


async def sync_bank_connection(
    session: AsyncSession,
    connection_id: uuid.UUID,
    pin: str | None = None,
    since_days: int | None = None,
) -> tuple[bool, str, AuthResult | None]:
    """Execute transaction sync for a bank connection.

    Enforces rate limiting (max 1 sync per connection per hour).
    Uses the stored encrypted PIN when `pin` is omitted.
    """
    stmt = select(BankConnection).where(BankConnection.id == connection_id)
    result = await session.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn or not conn.is_active:
        return False, "Bank connection not found or inactive.", None

    pin = (pin or "").strip() or connection_pin(conn)
    if not pin:
        return (
            False,
            "No stored PIN. Link the bank once more in the web app "
            "(Banking → Link account) so chat can refresh later.",
            None,
        )

    # Rate limiting check
    rate_key = f"rate_limit:bank_sync:{connection_id}"
    if not await rate_limit_check(rate_key, max_calls=1, window_seconds=3600):
        last = conn.last_synced_at.isoformat() if conn.last_synced_at else "never"
        return False, f"Rate limit reached. Please wait an hour between bank syncs. Last sync: {last}.", None

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
    summary = await _execute_import(session, conn, adapter, auth_res.session_data, since_days)
    return True, _sync_message(summary), auth_res


async def complete_tan_sync(
    session: AsyncSession,
    connection_id: uuid.UUID,
    session_data: dict,
    tan: str,
    since_days: int | None = None,
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

    summary = await _execute_import(session, conn, adapter, session_data, since_days)
    return True, _sync_message(summary, after_tan=True)


async def start_household_sync(session: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """Start a FinTS refresh for chat or /sync. Never asks for a PIN."""
    pending = get_pending_sync(user_id)
    if pending:
        return {
            "status": "needs_approval",
            "bank": pending.get("bank_name") or "DKB",
            "message": (
                "A bank login is already waiting. Approve it in the DKB app, "
                "then confirm the sync. Do not type a PIN or TAN."
            ),
        }

    connections = await list_active_connections(session, user_id)
    if not connections:
        return {
            "status": "no_connection",
            "message": "No bank is linked. Open Banking in the web app and tap Link account.",
        }

    results: list[dict[str, Any]] = []
    for conn in connections:
        pin = connection_pin(conn)
        if not pin:
            results.append(
                {
                    "status": "missing_pin",
                    "bank": conn.bank_name,
                    "last_synced_at": conn.last_synced_at.isoformat() if conn.last_synced_at else None,
                    "message": (
                        "The PIN is not stored for this bank yet. Link it once more in the web app "
                        "(Banking → Link account). After that, chat and /sync can refresh without asking for the PIN."
                    ),
                }
            )
            continue

        ok, msg, auth = await sync_bank_connection(session, conn.id, pin)
        if not ok:
            results.append({"status": "error", "bank": conn.bank_name, "message": msg})
            continue
        if auth and auth.requires_tan:
            put_pending_sync(
                user_id,
                {
                    "connection_id": conn.id,
                    "session_data": auth.session_data,
                    "bank_name": conn.bank_name,
                },
            )
            results.append(
                {
                    "status": "needs_approval",
                    "bank": conn.bank_name,
                    "message": (
                        "Approve the login in the DKB banking app, then confirm the bank sync. "
                        "Do not type a PIN or TAN."
                    ),
                }
            )
            break
        results.append({"status": "synced", "bank": conn.bank_name, "message": msg})

    if len(results) == 1:
        return results[0]
    if not results:
        return {"status": "no_connection", "message": "No active bank connection."}
    return {"status": "multi", "connections": results}


async def confirm_household_sync(session: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """Finish a sync after the user approved the login in the banking app."""
    pending = get_pending_sync(user_id)
    if not pending:
        return {
            "status": "idle",
            "message": "No bank login is waiting. Ask to refresh bank data first.",
        }

    ok, msg = await complete_tan_sync(
        session,
        pending["connection_id"],
        pending["session_data"],
        "",
    )
    if not ok:
        return {"status": "error", "bank": pending.get("bank_name"), "message": msg}

    pop_pending_sync(user_id)
    return {"status": "synced", "bank": pending.get("bank_name"), "message": msg}


def _sync_message(summary: dict[str, Any], after_tan: bool = False) -> str:
    prefix = "Sync completed after app approval." if after_tan else "Sync completed."
    return (
        f"{prefix} {summary['new_transactions']} new transactions "
        f"across {summary['accounts']} accounts (since {summary['since']})."
    )


async def _execute_import(
    session: AsyncSession,
    conn: BankConnection,
    adapter: FinTSAdapter,
    session_data: dict,
    since_days: int | None,
) -> dict[str, Any]:
    """Internal helper to pull accounts & transactions from connected adapter."""
    imported_total = 0
    accounts_seen = 0
    classified = 0
    since_date = (
        date.today() - timedelta(days=since_days)
        if since_days is not None
        else import_since_date()
    )
    try:
        conn.sync_status = "syncing"
        await session.flush()

        accounts = await adapter.fetch_accounts(session_data)

        for b_acc in accounts:
            # Match existing user account by IBAN or create new one
            acc = await find_account_by_iban(session, b_acc.iban, user_id=conn.user_id)

            if not acc and b_acc.iban:
                acc = await create_account(
                    session=session,
                    user_id=conn.user_id,
                    name=f"{conn.bank_name} ({b_acc.iban[-4:]})",
                    iban=b_acc.iban,
                    currency=b_acc.currency,
                    initial_balance=float(b_acc.balance) if b_acc.balance is not None else 0.0,
                )

            if not acc:
                continue

            accounts_seen += 1

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
                    imported_total += 1
                except ValueError:
                    # Duplicate skipped
                    pass

            if b_acc.balance is not None:
                tx_sum_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.account_id == acc.id
                )
                tx_sum = (await session.execute(tx_sum_stmt)).scalar() or 0
                acc.initial_balance = b_acc.balance - Decimal(str(tx_sum))
                logger.info(
                    "Set %s initial_balance=%s so ledger matches live balance %s",
                    acc.name,
                    acc.initial_balance,
                    b_acc.balance,
                )

        classified = await reclassify_user_transactions(session, conn.user_id)
        logger.info("Auto-classified %d transactions after sync", classified)

        conn.sync_status = "idle"
        conn.last_synced_at = datetime.now(UTC)
        conn.last_error = None
        await session.flush()

    finally:
        await adapter.disconnect(session_data)

    return {
        "accounts": accounts_seen,
        "new_transactions": imported_total,
        "classified": classified,
        "since": str(since_date),
    }
