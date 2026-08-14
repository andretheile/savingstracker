"""Resolve a Google identity to a household User."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import AuthIdentity, HouseholdInvite
from src.config import settings
from src.users.credentials import copy_legacy_secrets_if_empty
from src.users.models import User
from src.users.service import get_user_by_id, list_active_users


class AuthDeniedError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


async def get_identity_by_email(session: AsyncSession, email: str) -> AuthIdentity | None:
    stmt = select(AuthIdentity).where(AuthIdentity.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_invite_by_email(session: AsyncSession, email: str) -> HouseholdInvite | None:
    stmt = select(HouseholdInvite).where(HouseholdInvite.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def count_identities(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(AuthIdentity))
    return int(result.scalar_one())


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


async def list_household_identities(session: AsyncSession, user_id: uuid.UUID) -> list[AuthIdentity]:
    stmt = select(AuthIdentity).where(AuthIdentity.user_id == user_id).order_by(AuthIdentity.created_at)
    return list((await session.execute(stmt)).scalars().all())


async def list_household_invites(session: AsyncSession, user_id: uuid.UUID) -> list[HouseholdInvite]:
    stmt = (
        select(HouseholdInvite)
        .where(HouseholdInvite.user_id == user_id)
        .order_by(HouseholdInvite.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def create_household_invite(
    session: AsyncSession,
    user_id: uuid.UUID,
    email: str,
    invited_by_email: str,
) -> HouseholdInvite:
    email = normalize_email(email)
    if not email or "@" not in email:
        raise ValueError("Enter a valid email address.")
    existing = await get_identity_by_email(session, email)
    if existing is not None:
        if existing.user_id == user_id:
            raise ValueError("That email is already a member of this household.")
        raise ValueError("That email already belongs to another household.")
    pending = await get_invite_by_email(session, email)
    if pending is not None:
        if pending.user_id == user_id:
            return pending
        raise ValueError("That email already has a pending invite to another household.")
    invite = HouseholdInvite(user_id=user_id, email=email, invited_by_email=normalize_email(invited_by_email))
    session.add(invite)
    await session.flush()
    return invite


async def delete_household_invite(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    invite = await get_invite_by_email(session, email)
    if invite is None or invite.user_id != user_id:
        raise ValueError("Invite not found.")
    await session.delete(invite)
    await session.flush()


async def remove_household_member(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    identity = await get_identity_by_email(session, email)
    if identity is None or identity.user_id != user_id:
        raise ValueError("Member not found.")
    members = await list_household_identities(session, user_id)
    if len(members) <= 1:
        raise ValueError("Cannot remove the last household member.")
    await session.delete(identity)
    await session.flush()


async def resolve_google_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    picture: str | None,
    google_sub: str | None,
) -> User:
    email = normalize_email(email)
    if not email:
        raise AuthDeniedError("Google did not return an email address.")

    identity = await get_identity_by_email(session, email)
    if identity is not None:
        user = await get_user_by_id(session, identity.user_id)
        if user is None or not user.is_active:
            raise AuthDeniedError("This household is no longer active.")
        identity.name = name or identity.name
        identity.picture = picture
        if google_sub:
            identity.google_sub = google_sub
        await session.flush()
        return user

    allowed = settings.allowed_email_set
    invite = await get_invite_by_email(session, email)
    if invite is not None:
        user = await get_user_by_id(session, invite.user_id)
        if user is None or not user.is_active:
            raise AuthDeniedError("This household is no longer active.")
        session.add(
            AuthIdentity(
                user_id=user.id,
                email=email,
                google_sub=google_sub,
                name=name or email,
                picture=picture,
            )
        )
        await session.delete(invite)
        await session.flush()
        return user

    if allowed and email not in allowed:
        raise AuthDeniedError("This Google account is not allowed to use SavingsTracker.")

    if await count_identities(session) == 0 and await count_users(session) == 1:
        user = (await list_active_users(session))[0]
        copy_legacy_secrets_if_empty(user)
        if name and user.name == "Default User":
            user.name = name
        session.add(
            AuthIdentity(
                user_id=user.id,
                email=email,
                google_sub=google_sub,
                name=name or user.name,
                picture=picture,
            )
        )
        await session.flush()
        return user

    user = User(name=name or email.split("@")[0], telegram_id=None)
    session.add(user)
    await session.flush()
    session.add(
        AuthIdentity(
            user_id=user.id,
            email=email,
            google_sub=google_sub,
            name=name or user.name,
            picture=picture,
        )
    )
    await session.flush()
    return user
