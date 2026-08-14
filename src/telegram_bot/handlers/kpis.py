"""Telegram bot handler for /kpis and /newkpi commands."""

from datetime import date

from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import ContextTypes

from src.core.database import get_standalone_session
from src.kpis.engine import kpi_engine
from src.kpis.models import KPIDefinition
from src.kpis.service import evaluate_and_save_kpis_for_user
from src.telegram_bot.handlers.common import require_linked_user


async def kpis_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /kpis command. Displays active KPIs for current month."""
    if not update.effective_user or not update.effective_message:
        return

    user = await require_linked_user(update, context)
    if user is None:
        return

    async with get_standalone_session() as session:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1)) - date.resolution

        snapshots = await evaluate_and_save_kpis_for_user(
            session, user.id, first_day, last_day
        )

        kpi_lines = []
        for snap in snapshots:
            val = snap.value
            kpi_def = getattr(snap, "kpi_definition", None)
            unit = kpi_def.unit if kpi_def else ""
            name = kpi_def.name if kpi_def else "Metric"
            kpi_lines.append(f"• *{name}:* `{val:.1f}{unit}`")

    month_str = today.strftime("%B %Y")
    lines = [
        f"📊 *KPI Dashboard — {month_str}*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ] + kpi_lines
    lines.append("\n💡 Type /newkpi to add a custom metric formula!")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


async def newkpi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newkpi command. Explains formula syntax or saves custom KPI."""
    if not update.effective_user or not update.effective_message:
        return

    args = context.args or []
    if len(args) < 2:
        msg = (
            "🛠️ *Create Custom KPI*\n\n"
            "Usage: `/newkpi <Name> <Formula>`\n\n"
            "*Example:*\n"
            "`/newkpi Leisure_Share pct(category_dining_out_total + category_entertainment_total, total_expense)`\n\n"
            "*Available Variables:*\n"
            "`total_income`, `total_expense`, `net_cashflow`, `avg_expense`, `max_expense`, "
            "`category_<name>_total`\n\n"
            "*Built-in Functions:*\n"
            "`pct(part, whole)`, `change(current, previous)`, `abs(x)`, `min(a, b)`"
        )
        await update.effective_message.reply_text(msg, parse_mode="Markdown")
        return

    name = args[0].replace("_", " ")
    formula = " ".join(args[1:])

    is_valid, errors = kpi_engine.validate_formula(formula)
    if not is_valid:
        await update.effective_message.reply_text(
            f"❌ *Invalid Formula:*\n{', '.join(errors)}", parse_mode="Markdown"
        )
        return

    user = await require_linked_user(update, context)
    if user is None:
        return

    async with get_standalone_session() as session:
        kpi = KPIDefinition(
            user_id=user.id,
            name=name,
            formula=formula,
            unit="%",
        )
        session.add(kpi)

    await update.effective_message.reply_text(
        f"✅ Custom KPI *{name}* saved successfully!", parse_mode="Markdown"
    )
