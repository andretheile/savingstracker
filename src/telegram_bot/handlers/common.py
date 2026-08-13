"""Shared helpers for Telegram command handlers."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatType

from src.config import settings
from src.core.database import get_standalone_session
from src.users.models import User
from src.users.service import get_or_create_default_user, get_user_by_telegram_id

logger = logging.getLogger(__name__)

UNLINKED_MESSAGE = (
    "This Telegram account is not linked to SavingsTracker yet.\n\n"
    "Open the web app → Settings → Connect Telegram, then tap the link "
    "(or send /start with the code shown there)."
)

USER_NOT_ALLOWLISTED_MESSAGE = (
    "This Telegram account is linked, but it is not on the SavingsTracker allowlist."
)

GROUP_NOT_ALLOWLISTED_MESSAGE = (
    "This group is not allowed to use SavingsTracker.\n\n"
    "Chat id: {chat_id}\n"
    "Add it to TELEGRAM_ALLOWED_CHAT_IDS on the server if this is your household group."
)


def parse_id_set(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            logger.warning("Ignoring invalid Telegram id in allowlist: %s", part)
    return frozenset(ids)


def is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    return chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


async def authorize_telegram_user(update: Update) -> User | None:
    """Linked DMs, or anyone in an allowlisted household group."""
    if not update.effective_user or not update.effective_message:
        return None

    tg_id = update.effective_user.id
    chat = update.effective_chat
    chat_id = chat.id if chat is not None else None
    allowed_users = parse_id_set(settings.telegram_allowed_user_ids)
    allowed_chats = parse_id_set(settings.telegram_allowed_chat_ids)
    in_allowed_group = is_group_chat(update) and chat_id is not None and chat_id in allowed_chats

    async with get_standalone_session() as session:
        linked = await get_user_by_telegram_id(session, tg_id)

        if in_allowed_group:
            return linked or await get_or_create_default_user(session)

        if is_group_chat(update):
            logger.warning(
                "Denied Telegram group access chat_id=%s from_user=%s",
                chat_id,
                tg_id,
            )
            await update.effective_message.reply_text(
                GROUP_NOT_ALLOWLISTED_MESSAGE.format(chat_id=chat_id)
            )
            return None

        if linked is None:
            logger.warning("Denied unlinked Telegram user %s", tg_id)
            await update.effective_message.reply_text(UNLINKED_MESSAGE)
            return None

        if allowed_users and tg_id not in allowed_users:
            logger.warning("Denied Telegram user %s (not on user allowlist)", tg_id)
            await update.effective_message.reply_text(USER_NOT_ALLOWLISTED_MESSAGE)
            return None

        return linked


async def require_linked_user(update: Update) -> User | None:
    """Back-compat alias used by command handlers."""
    return await authorize_telegram_user(update)
