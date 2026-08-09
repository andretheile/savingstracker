"""Telegram bot handler for /start and /help commands."""

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database import get_standalone_session
from src.users.service import get_or_create_user_by_telegram_id


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command. Registers user and welcomes them."""
    if not update.effective_user or not update.effective_message:
        return

    tg_user = update.effective_user
    name = tg_user.first_name or tg_user.username or "User"

    async with get_standalone_session() as session:
        user = await get_or_create_user_by_telegram_id(session, tg_user.id, name)

    msg = (
        f"👋 Welcome to *SavingsTracker*, {user.name}!\n\n"
        "I'm your agentic financial assistant. I help you monitor accounts, "
        "classify spending, track custom KPIs, and project long-term savings growth.\n\n"
        "📌 *Quick Commands:*\n"
        "• /accounts — View & add bank accounts\n"
        "• /connect — Connect a German bank account via FinTS\n"
        "• /add — Log a manual transaction\n"
        "• /kpis — View live spending KPIs & savings rate\n"
        "• /newkpi — Create a custom KPI formula\n"
        "• /projection — Calculate long-term growth (MSCI World)\n"
        "• /balance — View your monthly balance sheet\n"
        "• /help — Show detailed help\n"
    )
    await update.effective_message.reply_text(msg, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_message:
        return

    msg = (
        "💡 *SavingsTracker Help*\n\n"
        "*Bank Connections*\n"
        "/connect — Link bank via FinTS/HBCI\n"
        "/sync — Trigger transaction update\n\n"
        "*Transactions*\n"
        "/add — Enter transaction manually\n"
        "/uncategorized — Review & classify uncategorized items\n\n"
        "*KPIs & Analytics*\n"
        "/kpis — Overview of key metrics\n"
        "/newkpi — Define custom metrics with formulas\n"
        "/projection — Scenario projections (MSCI World baseline)\n"
        "/balance — Monthly income vs expense summary\n"
    )
    await update.effective_message.reply_text(msg, parse_mode="Markdown")
