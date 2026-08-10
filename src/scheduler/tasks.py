"""Celery task definitions — Async worker jobs for periodic reports and background syncs."""

import asyncio
import logging
from datetime import date, datetime, timezone
import uuid

from telegram import Bot

from src.celery_app import celery_app
from src.config import settings
from src.core.database import get_standalone_session
from src.scheduler.models import MonthlyReport
from src.scheduler.monthly_report import build_monthly_report_payload
from src.users.service import list_active_users

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_all_monthly_reports(self):
    """Triggered on 1st of each month by Celery Beat.

    Queries all active users and dispatches individual report tasks.
    """
    async def _run():
        async with get_standalone_session() as session:
            users = await list_active_users(session)
            logger.info("Triggering monthly report for %d active users", len(users))
            for user in users:
                generate_user_monthly_report.delay(str(user.id))

    asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3, rate_limit="10/m")
def generate_user_monthly_report(self, user_id_str: str):
    """Generate and send monthly financial report for a single user."""
    user_id = uuid.UUID(user_id_str)

    async def _run():
        async with get_standalone_session() as session:
            # Determine previous month bounds
            today = date.today()
            first_of_this_month = today.replace(day=1)
            last_day_prev_month = first_of_this_month - date.resolution
            first_day_prev_month = last_day_prev_month.replace(day=1)

            payload, text_msg = await build_monthly_report_payload(
                session, user_id, first_day_prev_month, last_day_prev_month
            )

            # Record in DB
            report = MonthlyReport(
                user_id=user_id,
                report_month=first_day_prev_month,
                report_data=payload,
                computed_at=datetime.now(timezone.utc),
            )
            session.add(report)

            # Send via Telegram if token is set and user has Telegram ID
            from src.users.service import get_user_by_id
            user = await get_user_by_id(session, user_id)

            if user and user.telegram_id and settings.telegram_bot_token:
                try:
                    bot = Bot(token=settings.telegram_bot_token)
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text_msg,
                        parse_mode="Markdown",
                    )
                    report.sent_via_telegram = True
                    report.sent_at = datetime.now(timezone.utc)
                    logger.info("Sent monthly report to Telegram user %d", user.telegram_id)
                except Exception as e:
                    logger.error("Failed to send Telegram message to user %d: %s", user.telegram_id, e)

            await session.flush()

    asyncio.run(_run())


@celery_app.task
def check_stale_connections():
    """Daily check for bank connections that haven't synced in 30 days."""
    logger.info("Running daily stale connection check...")

    async def _run():
        from datetime import timedelta
        from sqlalchemy import select, or_
        from src.banking.models import BankConnection

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        async with get_standalone_session() as session:
            stmt = select(BankConnection).where(
                BankConnection.is_active.is_(True),
                or_(
                    BankConnection.last_synced_at < cutoff,
                    BankConnection.last_synced_at.is_(None),
                ),
            )
            result = await session.execute(stmt)
            stale_conns = result.scalars().all()

            logger.info("Found %d stale bank connections (>30 days since sync)", len(stale_conns))
            for conn in stale_conns:
                conn.sync_status = "stale"
                conn.last_error = "Connection idle over 30 days — re-authentication required."

            await session.flush()

    asyncio.run(_run())
