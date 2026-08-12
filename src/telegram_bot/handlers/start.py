"""Telegram bot handler for /start and /help commands."""

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database import get_standalone_session
from src.telegram_bot.linking import consume_link_code
from src.users.service import get_user_by_telegram_id, link_telegram_id


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start. Links this chat to the web app user when a pairing code is given."""
    if not update.effective_user or not update.effective_message:
        return

    tg_user = update.effective_user
    name = tg_user.first_name or tg_user.username or "User"
    args = context.args or []

    async with get_standalone_session() as session:
        if args:
            user_id = consume_link_code(args[0])
            if user_id is None:
                await update.effective_message.reply_text(
                    "That link code is invalid or expired. Open SavingsTracker and tap Connect Telegram again."
                )
                return
            user = await link_telegram_id(session, user_id, tg_user.id, name)
            user_name = user.name
            linked_now = True
        else:
            user = await get_user_by_telegram_id(session, tg_user.id)
            if user is None:
                await update.effective_message.reply_text(
                    "This Telegram account is not linked yet.\n\n"
                    "In SavingsTracker open Settings → Connect Telegram, then tap the link from there."
                )
                return
            user_name = user.name
            linked_now = False

    intro = (
        f"Linked to *{user_name}*. Household KPIs and the monthly digest use this chat."
        if linked_now
        else f"Welcome back, *{user_name}*."
    )
    msg = (
        f"{intro}\n\n"
        "Just send a message to ask about spending, recategorize a payment, "
        "or change household settings.\n"
        "In a group, @mention the bot or reply to it.\n\n"
        "📌 *Commands*\n"
        "• /kpis — Household KPIs for this month\n"
        "• /balance — Income vs expenses\n"
        "• /projection — Long-term savings projection\n"
        "• /newkpi — Add a custom KPI formula\n"
        "• /reset — Clear chat history\n"
        "• /help — Command list\n"
    )
    await update.effective_message.reply_text(msg, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_message:
        return

    msg = (
        "💡 *SavingsTracker*\n\n"
        "*Analytics*\n"
        "/kpis — Household KPIs\n"
        "/newkpi — Custom metric formula\n"
        "/projection — 20-year growth scenarios\n"
        "/balance — This month's income vs expenses\n"
        "/reset — Clear chat history\n\n"
        "Or just type a question in a private chat. In a group, @mention the bot "
        "or reply to one of its messages. Chat needs an OpenRouter key in the web app.\n\n"
        "Link this chat from the web app if /kpis says you are not connected."
    )
    await update.effective_message.reply_text(msg, parse_mode="Markdown")
