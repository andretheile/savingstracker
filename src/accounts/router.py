"""FastAPI router for Bank Account management."""

from decimal import Decimal
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.service import create_account, get_account_balance, list_user_accounts
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

    class Config:
        from_attributes = True


class AccountBalanceResponse(AccountResponse):
    current_balance: Decimal


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def api_create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
):
    acc = await create_account(
        db,
        user_id=data.user_id,
        name=data.name,
        iban=data.iban,
        currency=data.currency,
        initial_balance=data.initial_balance,
    )
    return acc


@router.get("/user/{user_id}", response_model=List[AccountBalanceResponse])
async def api_list_accounts(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
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
            current_balance=bal,
        )
        response.append(item)
    return response
