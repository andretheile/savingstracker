"""FastAPI router for Transactions."""

from datetime import date
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
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
    category_id: Optional[uuid.UUID] = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    category_id: Optional[uuid.UUID]
    transaction_date: date
    amount: float
    description: str
    counterparty: str
    reference: str
    is_manually_classified: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_add_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        tx = await add_transaction(
            db,
            user_id=data.user_id,
            account_id=data.account_id,
            tx_date=data.transaction_date,
            amount=data.amount,
            description=data.description,
            counterparty=data.counterparty,
            reference=data.reference,
            category_id=data.category_id,
        )
        return tx
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[TransactionResponse])
async def api_list_transactions(
    account_id: Optional[uuid.UUID] = None,
    category_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    txs = await list_transactions(
        db,
        account_id=account_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return txs
