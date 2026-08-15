"""FastAPI router for Bank Connection management and FinTS sync."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.accounts.service import create_account, find_account_by_iban, get_account_balance
from src.auth.dependencies import CurrentUser
from src.banking.adapters.fints_adapter import FinTSAdapter
from src.banking.models import BankConnection
from src.banking.service import (
    confirm_household_sync,
    import_since_date,
    start_household_sync,
    upsert_bank_connection,
)
from src.classification.service import IBAN_RE, normalize_iban, reclassify_user_transactions
from src.core.dependencies import get_db
from src.transactions.models import Transaction
from src.transactions.service import add_transaction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/banking", tags=["banking"])

# In-memory session store for active FinTS connections (keyed by connection_id)
_active_sessions: dict[str, dict[str, Any]] = {}


# ── Request / Response schemas ───────────────────────────

class BankConnectRequest(BaseModel):
    bank_blz: str
    login_name: str
    pin: str
    bank_name: str = "DKB"
    fints_url: str = ""


class TanSubmitRequest(BaseModel):
    session_id: str
    tan: str = ""


class BankConnectionResponse(BaseModel):
    id: str
    bank_blz: str
    bank_name: str
    sync_status: str
    is_active: bool
    last_synced_at: str | None = None
    last_error: str | None = None

    class Config:
        from_attributes = True


class ConnectResultResponse(BaseModel):
    success: bool
    session_id: str | None = None
    requires_tan: bool = False
    tan_challenge: str = ""
    tan_type: str = ""
    error: str = ""
    accounts_found: int = 0


class AccountSyncResponse(BaseModel):
    id: str
    name: str
    iban: str | None
    currency: str
    current_balance: float
    include_in_household: bool = True
    is_depot: bool = False


class DepotRegisterRequest(BaseModel):
    iban: str
    name: str = "DKB Depot"


class HouseholdSyncResponse(BaseModel):
    status: str
    message: str = ""
    bank: str | None = None
    last_synced_at: str | None = None
    connections: list[dict[str, Any]] | None = None


# ── Endpoints ────────────────────────────────────────────

@router.post("/connect", response_model=ConnectResultResponse)
async def api_connect_bank(
    data: BankConnectRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Step 1: Connect to bank via FinTS. Returns session_id if TAN required."""
    adapter = FinTSAdapter()

    # Attempt FinTS connection
    auth_result = await adapter.connect(
        bank_blz=data.bank_blz,
        fints_url=data.fints_url,
        login_name=data.login_name,
        pin=data.pin,
    )

    if not auth_result.success:
        return ConnectResultResponse(
            success=False,
            error=auth_result.error or "Connection failed",
        )

    # Generate a session ID and store the live FinTS client
    session_id = str(uuid.uuid4())
    _active_sessions[session_id] = {
        "client_session_data": auth_result.session_data,
        "adapter": adapter,
        "bank_blz": data.bank_blz,
        "bank_name": data.bank_name,
        "login_name": data.login_name,
        "pin": data.pin,
        "fints_url": data.fints_url,
        "user_id": user.id,
    }

    if auth_result.requires_tan:
        return ConnectResultResponse(
            success=True,
            session_id=session_id,
            requires_tan=True,
            tan_challenge=auth_result.tan_challenge,
            tan_type=auth_result.tan_type,
        )

    # No TAN needed — immediately fetch accounts
    accounts_count = await _fetch_and_store_accounts(db, session_id)
    return ConnectResultResponse(
        success=True,
        session_id=session_id,
        requires_tan=False,
        accounts_found=accounts_count,
    )


@router.post("/tan", response_model=ConnectResultResponse)
async def api_submit_tan(
    data: TanSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Step 2: Submit TAN / confirm App approval, then fetch accounts."""
    session = _active_sessions.get(data.session_id)
    if not session:
        return ConnectResultResponse(
            success=False,
            error="Session expired or invalid. Please reconnect.",
        )

    adapter: FinTSAdapter = session["adapter"]
    tan_result = await adapter.handle_tan(
        session["client_session_data"],
        data.tan,
    )

    if not tan_result.success:
        return ConnectResultResponse(
            success=False,
            error=tan_result.error or "TAN verification failed",
        )

    # TAN accepted — fetch accounts
    accounts_count = await _fetch_and_store_accounts(db, data.session_id)
    return ConnectResultResponse(
        success=True,
        session_id=data.session_id,
        requires_tan=False,
        accounts_found=accounts_count,
    )


@router.get("/accounts", response_model=list[AccountSyncResponse])
async def api_list_bank_accounts(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List synced bank accounts with current balances for this household."""
    stmt = select(Account).where(Account.is_active.is_(True), Account.user_id == user.id)
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    response = []
    for acc in accounts:
        bal = await get_account_balance(db, acc.id)
        response.append(AccountSyncResponse(
            id=str(acc.id),
            name=acc.name,
            iban=acc.iban,
            currency=acc.currency,
            current_balance=float(bal),
            include_in_household=bool(acc.include_in_household),
            is_depot=bool(acc.is_depot),
        ))
    return response


@router.post("/depot", response_model=AccountSyncResponse, status_code=status.HTTP_201_CREATED)
async def api_register_depot(
    data: DepotRegisterRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Register a depot by IBAN before FinTS lists it, so giro transfers can be tagged."""
    iban = normalize_iban(data.iban)
    if not IBAN_RE.fullmatch(iban):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a German IBAN (DE followed by 20 digits).",
        )

    name = (data.name or "").strip() or "DKB Depot"
    acc = await find_account_by_iban(db, iban, user_id=user.id)
    if acc:
        acc.iban = iban
        acc.is_depot = True
        acc.name = name
    else:
        acc = await create_account(
            db,
            user_id=user.id,
            name=name,
            iban=iban,
            is_depot=True,
            include_in_household=False,
        )
    await db.flush()
    await reclassify_user_transactions(db, user.id)
    bal = await get_account_balance(db, acc.id)
    return AccountSyncResponse(
        id=str(acc.id),
        name=acc.name,
        iban=acc.iban,
        currency=acc.currency,
        current_balance=float(bal),
        include_in_household=bool(acc.include_in_household),
        is_depot=bool(acc.is_depot),
    )


@router.post("/sync", response_model=HouseholdSyncResponse)
async def api_start_household_sync(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Refresh linked banks using the stored PIN. May require DKB app approval."""
    result = await start_household_sync(db, user.id)
    return HouseholdSyncResponse(**result)


@router.post("/sync/confirm", response_model=HouseholdSyncResponse)
async def api_confirm_household_sync(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Finish a sync after the user approved the login in the banking app."""
    result = await confirm_household_sync(db, user.id)
    return HouseholdSyncResponse(**result)


@router.get("/connections", response_model=list[BankConnectionResponse])
async def api_list_connections(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List bank connections for this household."""
    stmt = select(BankConnection).where(
        BankConnection.is_active.is_(True),
        BankConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    connections = result.scalars().all()

    return [
        BankConnectionResponse(
            id=str(c.id),
            bank_blz=c.bank_blz,
            bank_name=c.bank_name,
            sync_status=c.sync_status,
            is_active=c.is_active,
            last_synced_at=str(c.last_synced_at) if c.last_synced_at else None,
            last_error=c.last_error,
        )
        for c in connections
    ]


# ── Internal helpers ─────────────────────────────────────

async def _fetch_and_store_accounts(
    db: AsyncSession,
    session_id: str,
) -> int:
    """Use the live FinTS session to fetch accounts and persist them."""
    session = _active_sessions.get(session_id)
    if not session:
        return 0

    adapter: FinTSAdapter = session["adapter"]
    client_data = session["client_session_data"]

    try:
        bank_accounts = await adapter.fetch_accounts(client_data)
        logger.info("FinTS returned %d accounts", len(bank_accounts))

        user_id = session.get("user_id")
        if user_id is None:
            logger.error("FinTS session missing user_id")
            return 0
        from src.users.service import get_user_by_id

        user = await get_user_by_id(db, user_id)
        if user is None:
            logger.error("FinTS session user %s not found", user_id)
            return 0

        conn = await upsert_bank_connection(
            db,
            user_id=user.id,
            bank_blz=session["bank_blz"],
            bank_name=session["bank_name"],
            fints_url=session.get("fints_url", ""),
            login_name=session["login_name"],
            pin=session.get("pin"),
        )
        conn.sync_status = "idle"
        await db.flush()

        count = 0
        since = import_since_date()
        logger.info("Importing transactions since %s", since)
        for b_acc in bank_accounts:
            acc = None
            if b_acc.iban:
                acc = await find_account_by_iban(db, b_acc.iban, user_id=user.id)

            if acc is None:
                acc = await create_account(
                    session=db,
                    user_id=user.id,
                    name=f"{session['bank_name']} ({b_acc.iban[-4:] if b_acc.iban else 'N/A'})",
                    iban=b_acc.iban,
                    currency=b_acc.currency,
                    initial_balance=float(b_acc.balance) if b_acc.balance is not None else 0.0,
                )
                logger.info("Created account: %s (%s)", acc.name, b_acc.iban)
            else:
                logger.info("Updating existing account %s", b_acc.iban)

            if b_acc.iban:
                raw_txs = await adapter.fetch_transactions(client_data, b_acc.iban, since)
                imported = 0
                for r_tx in raw_txs:
                    try:
                        await add_transaction(
                            session=db,
                            user_id=user.id,
                            account_id=acc.id,
                            tx_date=r_tx.transaction_date,
                            amount=r_tx.amount,
                            description=r_tx.description,
                            counterparty=r_tx.counterparty,
                            reference=r_tx.reference,
                            bank_connection_id=conn.id,
                            auto_classify=True,
                        )
                        imported += 1
                    except ValueError:
                        pass
                logger.info("Imported %d new transactions for %s", imported, b_acc.iban)

            if b_acc.balance is not None:
                tx_sum_stmt = select(
                    func.coalesce(func.sum(Transaction.amount), 0)
                ).where(Transaction.account_id == acc.id)
                tx_sum = (await db.execute(tx_sum_stmt)).scalar() or 0
                acc.initial_balance = b_acc.balance - Decimal(str(tx_sum))
                logger.info(
                    "Set %s initial_balance=%s so ledger matches live balance %s",
                    acc.name,
                    acc.initial_balance,
                    b_acc.balance,
                )

            count += 1

        classified = await reclassify_user_transactions(db, user.id)
        logger.info("Auto-classified %d transactions after bank import", classified)
        return count

    except Exception as e:
        logger.error("Failed to fetch and store accounts: %s", e, exc_info=True)
        return 0
    finally:
        # Clean up the FinTS session
        try:
            await adapter.disconnect(client_data)
        except Exception:
            pass
        _active_sessions.pop(session_id, None)
