"""FastAPI dependencies for the signed-in household."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.users.models import User
from src.users.service import get_user_by_id


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    session_user = request.session.get("user") if hasattr(request, "session") else None
    if not isinstance(session_user, dict) or not session_user.get("user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        user_id = uuid.UUID(str(session_user["user_id"]))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_same_household(path_user_id: uuid.UUID, current: User) -> None:
    if path_user_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
