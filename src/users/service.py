"""User service — User management and Telegram ID resolution."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.models import User


async def get_or_create_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
    name: str,
) -> User:
    """Find a user by Telegram ID or create a new one."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            name=name,
        )
        session.add(user)
        await session.flush()

    return user


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Retrieve a user by primary key UUID."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_active_users(session: AsyncSession) -> Sequence[User]:
    """Retrieve all active users for periodic jobs."""
    stmt = select(User).where(User.is_active.is_(True))
    result = await session.execute(stmt)
    return result.scalars().all()
