"""FastAPI router for Transactions."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser, require_same_household
from src.classification.models import Category
from src.classification.service import reclassify_user_transactions
from src.core.dependencies import get_db
from src.transactions.models import Transaction
from src.transactions.service import add_transaction, list_transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionCreate(BaseModel):
    user_id: uuid.UUID
    account_id: uuid.UUID
    transaction_date: date
    amount: float
    description: str
    counterparty: str = ""
    reference: str = ""
    category_id: uuid.UUID | None = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str = ""
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    category_icon: str | None = None
    transaction_date: date
    amount: float
    description: str
    counterparty: str
    reference: str
    is_manually_classified: bool
    exclude_from_totals: bool = False
    category_direction: str | None = None

    class Config:
        from_attributes = True


def _to_response(tx: Transaction) -> TransactionResponse:
    account = getattr(tx, "account", None)
    category = getattr(tx, "category", None)
    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        account_name=account.name if account else "",
        category_id=tx.category_id,
        category_name=category.name if category else None,
        category_icon=category.icon if category else None,
        transaction_date=tx.transaction_date,
        amount=float(tx.amount),
        description=tx.description,
        counterparty=tx.counterparty,
        reference=tx.reference,
        is_manually_classified=tx.is_manually_classified,
        exclude_from_totals=bool(getattr(tx, "exclude_from_totals", False)),
        category_direction=category.direction if category else None,
    )


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_add_transaction(
    data: TransactionCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(data.user_id, user)
    try:
        tx = await add_transaction(
            db,
            user_id=user.id,
            account_id=data.account_id,
            tx_date=data.transaction_date,
            amount=data.amount,
            description=data.description,
            counterparty=data.counterparty,
            reference=data.reference,
            category_id=data.category_id,
        )
        loaded = await db.execute(
            select(Transaction)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
            .where(Transaction.id == tx.id)
        )
        return _to_response(loaded.scalar_one())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


class TransactionCategoryUpdate(BaseModel):
    category_name: str


@router.patch("/{tx_id}/category", response_model=TransactionResponse)
async def api_set_transaction_category(
    tx_id: uuid.UUID,
    data: TransactionCategoryUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
        .where(Transaction.id == tx_id)
    )
    tx = (await db.execute(stmt)).scalar_one_or_none()
    if not tx or tx.account is None or tx.account.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    cat_stmt = select(Category).where(Category.name == data.category_name).limit(1)
    category = (await db.execute(cat_stmt)).scalars().first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    tx.category_id = category.id
    tx.is_manually_classified = True
    await db.flush()
    tx.category = category
    return _to_response(tx)


class TransactionExcludeUpdate(BaseModel):
    exclude_from_totals: bool


@router.patch("/{tx_id}/exclude", response_model=TransactionResponse)
async def api_set_transaction_exclude(
    tx_id: uuid.UUID,
    data: TransactionExcludeUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
        .where(Transaction.id == tx_id)
    )
    tx = (await db.execute(stmt)).scalar_one_or_none()
    if not tx or tx.account is None or tx.account.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    tx.exclude_from_totals = data.exclude_from_totals
    await db.flush()
    return _to_response(tx)


@router.post("/reclassify")
async def api_reclassify_transactions(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(user_id, user)
    updated = await reclassify_user_transactions(db, user_id)
    return {"updated": updated}


@router.get("/", response_model=list[TransactionResponse])
async def api_list_transactions(
    user: CurrentUser,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    txs = await list_transactions(
        db,
        user_id=user.id,
        account_id=account_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [_to_response(tx) for tx in txs]
