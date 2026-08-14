"""FastAPI router for User management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser, require_same_household
from src.core.dependencies import get_db
from src.users.service import get_user_by_id

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    telegram_id: int | None
    timezone: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", status_code=status.HTTP_403_FORBIDDEN)
async def create_or_get_user():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Users are created by signing in with Google.",
    )


@router.get("/me", response_model=UserResponse)
async def read_current_user(user: CurrentUser):
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(user_id, user)
    found = await get_user_by_id(db, user_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return found
