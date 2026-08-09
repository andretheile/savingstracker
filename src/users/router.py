"""FastAPI router for User management."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.core.dependencies import get_db
from src.users.service import get_or_create_user_by_telegram_id, get_user_by_id

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: str
    telegram_id: int | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    telegram_id: int | None
    timezone: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    if not data.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="telegram_id is required for user creation",
        )
    user = await get_or_create_user_by_telegram_id(db, data.telegram_id, data.name)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
