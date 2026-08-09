"""Telegram bot handler for /balance command."""

from datetime import date
from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import ContextTypes

from src.balance_sheets.service import generate_balance_sheet
from src.core.database import get_standalone_session
from src.users.service import get_or_create_user_by_telegram_id


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /balance command. Formats monthly income vs expense balance sheet."""
    if not update.effective_user or not update.effective_message:
        return

    tg_user = update.effective_user

    async with get_standalone_session() as session:
        user = await get_or_create_user_by_telegram_id(
            session, tg_user.id, tg_user.first_name or "User"
        )

        today = date.today()
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1)) - date.resolution

        bs = await generate_balance_sheet(session, user.id, first_day, last_day)

    month_str = today.strftime("%B %Y")
    lines = [
        f"📋 *Balance Sheet — {month_str}*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Total Income:*   €{bs.total_income:,.2f}",
        f"💸 *Total Expenses:* €{bs.total_expense:,.2f}",
        f"📈 *Net Cashflow:*   €{bs.net_cashflow:,.2f} ({bs.savings_rate_pct:.1f}% saved)",
        "",
        "🏦 *Account Balances:*",
    ]

    for acc_name, bal in bs.account_balances.items():
        lines.append(f"  • {acc_name}: €{bal:,.2f}")

    if bs.income_items:
        lines.extend(["", "💵 *Income Breakdown:*"])
        for item in bs.income_items:
            lines.append(f"  • {item.icon} {item.category_name}: €{item.amount:,.2f}")

    if bs.expense_items:
        lines.extend(["", "🛒 *Expense Breakdown:*"])
        for item in bs.expense_items:
            lines.append(f"  • {item.icon} {item.category_name}: €{item.amount:,.2f}")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")
