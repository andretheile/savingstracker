"""Telegram /sync and /syncconfirm — FinTS refresh without the LLM."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.banking.service import confirm_household_sync, start_household_sync
from src.core.database import get_standalone_session
from src.telegram_bot.handlers.common import require_linked_user


def format_sync_result(result: dict) -> str:
    status = result.get("status")
    message = result.get("message") or ""
    bank = result.get("bank") or "DKB"

    if status == "needs_approval":
        return (
            f"{bank} is waiting for you to confirm the login in the banking app.\n\n"
            "Approve it there, then send /syncconfirm — or tell me in chat that you approved it."
        )
    if status == "missing_pin":
        return (
            "The bank PIN is not stored yet, so chat cannot refresh FinTS on its own.\n\n"
            "Open SavingsTracker → Banking → Link account once more. "
            "After that, /sync and chat can refresh without asking for the PIN."
        )
    if status == "no_connection":
        return "No bank is linked yet. Open SavingsTracker → Banking → Link account."
    if status == "idle":
        return message or "Nothing to confirm. Send /sync first."
    if status == "error":
        return message or "Bank sync failed."
    if status == "synced":
        return message or f"{bank} synced."
    if status == "multi":
        lines = [format_sync_result(item) for item in result.get("connections") or []]
        return "\n\n".join(lines) or "Bank sync finished."
    return message or "Bank sync finished."


async def sync_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    user = await require_linked_user(update, context)
    if user is None:
        return

    await update.effective_message.reply_text("Connecting to the bank… this can take a minute.")
    async with get_standalone_session() as session:
        result = await start_household_sync(session, user.id)
        await session.commit()
    await update.effective_message.reply_text(format_sync_result(result))


async def syncconfirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    user = await require_linked_user(update, context)
    if user is None:
        return

    await update.effective_message.reply_text("Waiting for DKB app approval, then importing…")
    async with get_standalone_session() as session:
        result = await confirm_household_sync(session, user.id)
        await session.commit()
    await update.effective_message.reply_text(format_sync_result(result))
