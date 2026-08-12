"""Shared helpers for Telegram command handlers."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ChatType

from src.core.database import get_standalone_session
from src.users.models import User
from src.users.service import get_or_create_default_user, get_user_by_telegram_id

UNLINKED_MESSAGE = (
    "This Telegram account is not linked to SavingsTracker yet.\n\n"
    "Open the web app → Settings → Connect Telegram, then tap the link "
    "(or send /start with the code shown there)."
)


def is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    return chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


async def require_linked_user(update: Update) -> User | None:
    """Return the SavingsTracker user for this chat, or tell them to link first."""
    if not update.effective_user or not update.effective_message:
        return None
    async with get_standalone_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if user is None:
            await update.effective_message.reply_text(UNLINKED_MESSAGE)
            return None
        return user


async def resolve_finance_user(update: Update) -> User | None:
    """Linked Telegram user, or the household default user in a group."""
    if not update.effective_user or not update.effective_message:
        return None
    async with get_standalone_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if user is not None:
            return user
        if is_group_chat(update):
            return await get_or_create_default_user(session)
    await update.effective_message.reply_text(UNLINKED_MESSAGE)
    return None
