"""Telegram bot initialization, polling lifecycle, and per-household tokens."""

from __future__ import annotations

import logging
import uuid

from telegram import Bot
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.config import settings
from src.core.envfile import persist_env_value
from src.telegram_bot.handlers.balance import balance_handler
from src.telegram_bot.handlers.chat import chat_handler, reset_handler
from src.telegram_bot.handlers.kpis import kpis_handler, newkpi_handler
from src.telegram_bot.handlers.projections import projection_handler
from src.telegram_bot.handlers.start import help_handler, start_handler
from src.telegram_bot.handlers.sync import sync_handler, syncconfirm_handler
from src.telegram_bot.linking import set_bot_identity
from src.users.credentials import telegram_token_for_user

logger = logging.getLogger(__name__)

_bot_apps: dict[uuid.UUID, Application] = {}
_legacy_app: Application | None = None


def create_telegram_bot(
    token: str | None = None,
    household_user_id: uuid.UUID | None = None,
) -> Application | None:
    bot_token = token if token is not None else settings.telegram_bot_token
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return None
    app = ApplicationBuilder().token(bot_token).build()
    if household_user_id is not None:
        app.bot_data["household_user_id"] = str(household_user_id)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("kpis", kpis_handler))
    app.add_handler(CommandHandler("newkpi", newkpi_handler))
    app.add_handler(CommandHandler("projection", projection_handler))
    app.add_handler(CommandHandler("balance", balance_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("sync", sync_handler))
    app.add_handler(CommandHandler("syncconfirm", syncconfirm_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    logger.info("Telegram bot initialized with registered handlers.")
    return app


def bot_is_running() -> bool:
    return bool(_bot_apps) or _legacy_app is not None


def bot_is_running_for_user(user_id: uuid.UUID) -> bool:
    return user_id in _bot_apps


async def start_polling(token: str | None = None) -> str | None:
    """Legacy single-bot start used by tests. Prefer start_polling_for_user."""
    global _legacy_app
    await stop_polling()
    bot_token = token if token is not None else settings.telegram_bot_token
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return None
    app = create_telegram_bot(bot_token)
    await app.initialize()
    me = await app.bot.get_me()
    set_bot_identity(me.username, me.first_name)
    await app.start()
    if app.updater:
        await app.updater.start_polling(allowed_updates=["message", "edited_message"])
    _legacy_app = app
    logger.info("Telegram bot polling started as @%s", me.username)
    return me.username


async def start_polling_for_user(
    user_id: uuid.UUID,
    token: str,
    username: str | None = None,
) -> str | None:
    await stop_polling_for_user(user_id)
    app = create_telegram_bot(token, household_user_id=user_id)
    if app is None:
        return None
    await app.initialize()
    me = await app.bot.get_me()
    await app.start()
    if app.updater:
        await app.updater.start_polling(allowed_updates=["message", "edited_message"])
    _bot_apps[user_id] = app
    logger.info("Telegram bot polling started as @%s for household %s", me.username, user_id)
    return me.username or username


async def stop_polling_for_user(user_id: uuid.UUID) -> None:
    app = _bot_apps.pop(user_id, None)
    if app is None:
        return
    try:
        if app.updater:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
    except Exception:
        logger.exception("Error while stopping Telegram bot for %s", user_id)


async def start_all_household_bots() -> None:
    from src.core.database import get_standalone_session
    from src.users.service import list_active_users

    async with get_standalone_session() as session:
        users = await list_active_users(session)
        for user in users:
            token = telegram_token_for_user(user)
            if not token:
                continue
            try:
                username = await start_polling_for_user(user.id, token, username=user.telegram_bot_username)
                if username and user.telegram_bot_username != username:
                    user.telegram_bot_username = username
            except Exception:
                logger.exception("Failed to start Telegram bot for household %s", user.id)


async def stop_polling() -> None:
    global _legacy_app
    for user_id in list(_bot_apps):
        await stop_polling_for_user(user_id)
    if _legacy_app is None:
        set_bot_identity(None, None)
        return
    try:
        if _legacy_app.updater:
            await _legacy_app.updater.stop()
        await _legacy_app.stop()
        await _legacy_app.shutdown()
    except Exception:
        logger.exception("Error while stopping Telegram bot")
    _legacy_app = None
    set_bot_identity(None, None)


async def validate_bot_token(token: str) -> str:
    """Return the bot username if the token is valid."""
    bot = Bot(token=token)
    me = await bot.get_me()
    if not me.username:
        raise ValueError("Telegram did not return a bot username")
    return me.username


def persist_bot_token(token: str) -> None:
    """Write TELEGRAM_BOT_TOKEN into the project .env without logging the secret."""
    persist_env_value("TELEGRAM_BOT_TOKEN", token)
