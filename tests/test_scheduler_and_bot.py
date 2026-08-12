"""Unit tests for monthly report generator, demo seed script, and Celery tasks."""

from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.accounts.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.kpis.models  # noqa
import src.projections.models  # noqa
import src.scheduler.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.core.base_model import Base
from src.scheduler.monthly_report import build_monthly_report_payload
from src.seed import run_seed
from src.telegram_bot.bot import create_telegram_bot
from src.users.service import get_or_create_user_by_telegram_id


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_monthly_report_payload_builder(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 12345, "Digest User")
    
    payload, text_msg = await build_monthly_report_payload(
        async_session, user.id, date(2026, 8, 1), date(2026, 8, 31)
    )
    assert payload["month"] == "August 2026"
    assert "Monthly Report" in text_msg


@pytest.mark.asyncio
async def test_seed_demo_data_script(async_session: AsyncSession):
    class DummyCtx:
        async def __aenter__(self):
            return async_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.seed.get_standalone_session", return_value=DummyCtx()):
        await run_seed()


def test_telegram_bot_factory():
    # Token set
    with patch("src.telegram_bot.bot.settings.telegram_bot_token", "123456789:TestToken"):
        bot_app = create_telegram_bot()
        assert bot_app is not None

    # Token empty
    with patch("src.telegram_bot.bot.settings.telegram_bot_token", ""):
        bot_app_none = create_telegram_bot()
        assert bot_app_none is None
