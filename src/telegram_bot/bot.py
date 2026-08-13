"""Telegram bot initialization, polling lifecycle, and token persistence."""

from __future__ import annotations

import logging

from telegram import Bot
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.config import settings
from src.core.envfile import persist_env_value
from src.telegram_bot.handlers.balance import balance_handler
from src.telegram_bot.handlers.chat import chat_handler, reset_handler
from src.telegram_bot.handlers.kpis import kpis_handler, newkpi_handler
from src.telegram_bot.handlers.projections import projection_handler
from src.telegram_bot.handlers.start import help_handler, start_handler
from src.telegram_bot.linking import set_bot_identity

logger = logging.getLogger(__name__)

_bot_app: Application | None = None


def create_telegram_bot(token: str | None = None) -> Application | None:
    """Initialize and build the python-telegram-bot Application instance."""
    bot_token = token if token is not None else settings.telegram_bot_token
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return None

    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("kpis", kpis_handler))
    app.add_handler(CommandHandler("newkpi", newkpi_handler))
    app.add_handler(CommandHandler("projection", projection_handler))
    app.add_handler(CommandHandler("balance", balance_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    logger.info("Telegram bot initialized with registered handlers.")
    return app


def bot_is_running() -> bool:
    return _bot_app is not None


async def start_polling(token: str | None = None) -> str | None:
    """Start (or restart) bot polling. Returns the bot username."""
    global _bot_app
    await stop_polling()

    app = create_telegram_bot(token)
    if app is None:
        return None

    await app.initialize()
    me = await app.bot.get_me()
    set_bot_identity(me.username, me.first_name)
    await app.start()
    if app.updater:
        await app.updater.start_polling(allowed_updates=["message", "edited_message"])
    _bot_app = app
    logger.info("Telegram bot polling started as @%s", me.username)
    return me.username


async def stop_polling() -> None:
    global _bot_app
    if _bot_app is None:
        return
    try:
        if _bot_app.updater:
            await _bot_app.updater.stop()
        await _bot_app.stop()
        await _bot_app.shutdown()
    except Exception:
        logger.exception("Error while stopping Telegram bot")
    _bot_app = None
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
