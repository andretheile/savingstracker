"""Telegram bot initialization and handler registration."""

import logging
from telegram.ext import Application, ApplicationBuilder, CommandHandler

from src.config import settings
from src.telegram_bot.handlers.balance import balance_handler
from src.telegram_bot.handlers.kpis import kpis_handler, newkpi_handler
from src.telegram_bot.handlers.projections import projection_handler
from src.telegram_bot.handlers.start import help_handler, start_handler

logger = logging.getLogger(__name__)


def create_telegram_bot() -> Application | None:
    """Initialize and build the python-telegram-bot Application instance."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return None

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("kpis", kpis_handler))
    app.add_handler(CommandHandler("newkpi", newkpi_handler))
    app.add_handler(CommandHandler("projection", projection_handler))
    app.add_handler(CommandHandler("balance", balance_handler))

    logger.info("Telegram bot initialized with registered handlers.")
    return app
