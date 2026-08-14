"""FastAPI router for Bank Account management."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.accounts.service import create_account, get_account_balance, list_user_accounts
from src.auth.dependencies import CurrentUser, require_same_household
from src.classification.service import reclassify_user_transactions
from src.core.dependencies import get_db

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    iban: str | None = None
    currency: str = "EUR"
    initial_balance: float = 0.0


class AccountResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    iban: str | None
    currency: str
    initial_balance: float
    is_active: bool
    include_in_household: bool = True
    is_depot: bool = False

    class Config:
        from_attributes = True


class AccountBalanceResponse(AccountResponse):
    current_balance: Decimal


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def api_create_account(
    data: AccountCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(data.user_id, user)
    acc = await create_account(
        db,
        user_id=data.user_id,
        name=data.name,
        iban=data.iban,
        currency=data.currency,
        initial_balance=data.initial_balance,
    )
    return acc


@router.get("/{account_id}", response_model=AccountBalanceResponse)
async def api_get_account(
    account_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Account).where(Account.id == account_id, Account.is_active.is_(True))
    result = await db.execute(stmt)
    acc = result.scalar_one_or_none()
    if not acc or acc.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    bal = await get_account_balance(db, acc.id)
    return AccountBalanceResponse(
        id=acc.id,
        user_id=acc.user_id,
        name=acc.name,
        iban=acc.iban,
        currency=acc.currency,
        initial_balance=float(acc.initial_balance),
        is_active=acc.is_active,
        include_in_household=bool(acc.include_in_household),
        is_depot=bool(acc.is_depot),
        current_balance=bal,
    )


@router.get("/user/{user_id}", response_model=list[AccountBalanceResponse])
async def api_list_accounts(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(user_id, user)
    accounts = await list_user_accounts(db, user_id)
    response = []
    for acc in accounts:
        bal = await get_account_balance(db, acc.id)
        item = AccountBalanceResponse(
            id=acc.id,
            user_id=acc.user_id,
            name=acc.name,
            iban=acc.iban,
            currency=acc.currency,
            initial_balance=float(acc.initial_balance),
            is_active=acc.is_active,
            include_in_household=bool(acc.include_in_household),
            is_depot=bool(acc.is_depot),
            current_balance=bal,
        )
        response.append(item)
    return response


class AccountHouseholdUpdate(BaseModel):
    include_in_household: bool


class AccountDepotUpdate(BaseModel):
    is_depot: bool


@router.patch("/{account_id}/household", response_model=AccountResponse)
async def api_set_account_household(
    account_id: uuid.UUID,
    data: AccountHouseholdUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Account).where(Account.id == account_id)
    acc = (await db.execute(stmt)).scalar_one_or_none()
    if not acc or acc.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    acc.include_in_household = data.include_in_household
    await db.flush()
    return acc


@router.patch("/{account_id}/depot", response_model=AccountResponse)
async def api_set_account_depot(
    account_id: uuid.UUID,
    data: AccountDepotUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Account).where(Account.id == account_id)
    acc = (await db.execute(stmt)).scalar_one_or_none()
    if not acc or acc.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    acc.is_depot = data.is_depot
    await db.flush()
    await reclassify_user_transactions(db, acc.user_id)
    return acc
