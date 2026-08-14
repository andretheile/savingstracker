"""Telegram bot handler for /projection command."""

from datetime import date

from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import ContextTypes

from src.core.database import get_standalone_session
from src.projections.service import generate_user_projection
from src.telegram_bot.handlers.common import require_linked_user


async def projection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /projection command. Displays long-term compound growth and scenario analysis."""
    if not update.effective_user or not update.effective_message:
        return

    user = await require_linked_user(update, context)
    if user is None:
        return

    async with get_standalone_session() as session:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1)) - date.resolution

        proj_data, _ = await generate_user_projection(session, user.id, first_day, last_day)

    base = proj_data.baseline
    lines = [
        "🔮 *Savings Projection — 20-Year Horizon*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Current Monthly Savings:* €{proj_data.monthly_contribution:,.2f}",
        "📈 *Benchmark Return:* MSCI World (7.0% nominal / 2.0% inflation)",
        "",
        "📊 *Baseline Projection (20 Years):*",
        f"  • Nominal Portfolio Value: *€{base.nominal:,.2f}*",
        f"  • Inflation-Adjusted (Real): *€{base.real:,.2f}*",
        f"  • Total Contributions: €{base.total_contributed:,.2f}",
        f"  • Compound Growth Interest: €{base.total_growth:,.2f}",
        "",
        "📈 *What-if Scenarios (Real Purchasing Power):*",
    ]

    for sc in proj_data.scenarios:
        sign = "+" if sc.delta_vs_baseline_real >= 0 else ""
        lines.append(
            f"  • *{sc.label}:* €{sc.result.real:,.2f} ({sign}€{sc.delta_vs_baseline_real:,.2f})"
        )

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")
