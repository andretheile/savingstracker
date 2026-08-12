"""FastAPI router for Bank Connection management and FinTS sync."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.banking.adapters.fints_adapter import FinTSAdapter
from src.banking.models import BankConnection
from src.banking.service import create_bank_connection
from src.core.dependencies import get_db
from src.core.security import encrypt_field
from src.accounts.models import Account
from src.accounts.service import create_account, get_account_balance

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
    tan: str


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


# ── Endpoints ────────────────────────────────────────────

@router.post("/connect", response_model=ConnectResultResponse)
async def api_connect_bank(
    data: BankConnectRequest,
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
        "fints_url": data.fints_url,
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
    db: AsyncSession = Depends(get_db),
):
    """List all synced bank accounts with current balances."""
    stmt = select(Account).where(Account.is_active.is_(True))
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
        ))
    return response


@router.get("/connections", response_model=list[BankConnectionResponse])
async def api_list_connections(
    db: AsyncSession = Depends(get_db),
):
    """List all bank connections."""
    stmt = select(BankConnection).where(BankConnection.is_active.is_(True))
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

        # Create a default user if none exists (single-user mode for now)
        from src.users.models import User
        stmt = select(User).limit(1)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            user = User(name="Default User", telegram_id=None)
            db.add(user)
            await db.flush()

        # Persist bank connection
        conn = BankConnection(
            user_id=user.id,
            bank_blz=session["bank_blz"],
            bank_name=session["bank_name"],
            fints_url=session.get("fints_url", ""),
            login_name=encrypt_field(session["login_name"]),
            adapter_type="fints",
            sync_status="idle",
        )
        db.add(conn)
        await db.flush()

        count = 0
        for b_acc in bank_accounts:
            # Check if account already exists by IBAN
            if b_acc.iban:
                existing_stmt = select(Account).where(Account.iban == b_acc.iban)
                existing_result = await db.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()
                if existing:
                    logger.info("Account %s already exists, skipping", b_acc.iban)
                    count += 1
                    continue

            acc = await create_account(
                session=db,
                user_id=user.id,
                name=f"{session['bank_name']} ({b_acc.iban[-4:] if b_acc.iban else 'N/A'})",
                iban=b_acc.iban,
                currency=b_acc.currency,
            )
            count += 1
            logger.info("Created account: %s (%s)", acc.name, b_acc.iban)

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
