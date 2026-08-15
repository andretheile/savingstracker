"""Unit tests for Telegram bot handlers and Celery tasks."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

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
from src.celery_app import celery_app
from src.core.base_model import Base
from src.scheduler.tasks import (
    check_stale_connections,
    generate_all_monthly_reports,
    generate_user_monthly_report,
)
from src.telegram_bot.handlers.balance import balance_handler
from src.telegram_bot.handlers.common import parse_id_set
from src.telegram_bot.handlers.kpis import kpis_handler, newkpi_handler
from src.telegram_bot.handlers.projections import projection_handler
from src.telegram_bot.handlers.start import help_handler, start_handler
from src.telegram_bot.handlers.sync import format_sync_result, sync_handler, syncconfirm_handler
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
async def test_telegram_all_handlers(async_session: AsyncSession):
    # Seed user inside session
    await get_or_create_user_by_telegram_id(async_session, 999111, "Bot User")

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 999111
    update.effective_user.first_name = "Bot User"
    update.message = MagicMock()
    update.message.text = "/start"

    reply_mock = AsyncMock()
    update.message.reply_text = reply_mock
    update.effective_message = MagicMock()
    update.effective_message.reply_text = reply_mock

    context = MagicMock()
    context.args = []

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    with patch("src.telegram_bot.handlers.start.get_standalone_session", side_effect=mock_standalone), \
         patch("src.telegram_bot.handlers.common.get_standalone_session", side_effect=mock_standalone), \
         patch("src.telegram_bot.handlers.kpis.get_standalone_session", side_effect=mock_standalone), \
         patch("src.telegram_bot.handlers.projections.get_standalone_session", side_effect=mock_standalone), \
         patch("src.telegram_bot.handlers.balance.get_standalone_session", side_effect=mock_standalone):

        # /start
        await start_handler(update, context)
        assert reply_mock.called

        # /help
        await help_handler(update, context)
        assert reply_mock.called

        # /kpis
        await kpis_handler(update, context)
        assert reply_mock.called

        # /newkpi valid
        context.args = ["Rate", "=", "total_income"]
        update.message.text = "/newkpi Rate = total_income"
        await newkpi_handler(update, context)
        assert reply_mock.called

        # /projection
        await projection_handler(update, context)
        assert reply_mock.called

        # /balance
        await balance_handler(update, context)
        assert reply_mock.called


def test_format_sync_result_copy():
    assert "banking app" in format_sync_result({"status": "needs_approval", "bank": "DKB"}).lower()
    assert "pin is not stored" in format_sync_result({"status": "missing_pin"}).lower()
    assert "no bank is linked" in format_sync_result({"status": "no_connection"}).lower()


@pytest.mark.asyncio
async def test_sync_handlers(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 999111, "Bot User")
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 999111
    reply_mock = AsyncMock()
    update.effective_message = MagicMock()
    update.effective_message.reply_text = reply_mock
    context = MagicMock()

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    with (
        patch("src.telegram_bot.handlers.sync.require_linked_user", AsyncMock(return_value=user)),
        patch("src.telegram_bot.handlers.sync.get_standalone_session", side_effect=mock_standalone),
        patch(
            "src.telegram_bot.handlers.sync.start_household_sync",
            AsyncMock(return_value={"status": "needs_approval", "bank": "DKB"}),
        ),
        patch(
            "src.telegram_bot.handlers.sync.confirm_household_sync",
            AsyncMock(return_value={"status": "synced", "message": "Sync completed."}),
        ),
    ):
        await sync_handler(update, context)
        await syncconfirm_handler(update, context)
    texts = [call.args[0] for call in reply_mock.await_args_list]
    assert any("Connecting to the bank" in t for t in texts)
    assert any("banking app" in t.lower() for t in texts)
    assert any("Sync completed" in t for t in texts)


def test_parse_id_set():
    assert parse_id_set("") == frozenset()
    assert parse_id_set("  ") == frozenset()
    assert parse_id_set("123, -1001; 456") == frozenset({123, -1001, 456})
    assert parse_id_set("12,nope,34") == frozenset({12, 34})


@pytest.mark.asyncio
async def test_unlinked_private_chat_is_denied(async_session: AsyncSession):
    from src.telegram_bot.handlers.chat import chat_handler

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 424242
    update.effective_chat = MagicMock()
    update.effective_chat.id = 424242
    update.effective_chat.type = "private"
    update.effective_message = MagicMock()
    update.effective_message.text = "what did we spend?"
    reply = AsyncMock()
    update.effective_message.reply_text = reply
    run_agent = AsyncMock(return_value="should not run")

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    with (
        patch(
            "src.telegram_bot.handlers.common.get_standalone_session",
            side_effect=mock_standalone,
        ),
        patch("src.telegram_bot.handlers.chat.run_agent", run_agent),
        patch("src.users.credentials.settings.openrouter_api_key", "sk-test"),
    ):
        await chat_handler(update, MagicMock())

    run_agent.assert_not_awaited()
    reply.assert_awaited()
    assert "not linked" in reply.await_args.args[0].lower()


def test_telegram_link_code_roundtrip():
    from src.telegram_bot.linking import consume_link_code, create_link_code

    user_id = uuid.uuid4()
    entry = create_link_code(user_id)
    assert consume_link_code("nope") is None
    assert consume_link_code(entry.code) == user_id
    assert consume_link_code(entry.code) is None


@pytest.mark.asyncio
async def test_start_without_link_asks_to_connect(async_session: AsyncSession):
    from src.users.service import get_or_create_default_user

    await get_or_create_default_user(async_session)

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 424242
    update.effective_user.first_name = "Andre"
    update.effective_user.username = "andre"
    reply_mock = AsyncMock()
    update.effective_message = MagicMock()
    update.effective_message.reply_text = reply_mock
    context = MagicMock()
    context.args = []

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    with patch("src.telegram_bot.handlers.start.get_standalone_session", side_effect=mock_standalone):
        await start_handler(update, context)

    text = reply_mock.call_args.args[0]
    assert "not linked" in text.lower()


@pytest.mark.asyncio
async def test_celery_task_wrapper_execution(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 888111, "Task User")

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    # Custom runner to execute task coroutine inside current running event loop
    def sync_runner(coro):
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(coro) if not loop.is_running() else None

    async def run_coro(coro):
        await coro

    with patch("src.scheduler.tasks.get_standalone_session", side_effect=mock_standalone), \
         patch("src.scheduler.tasks.generate_user_monthly_report.delay"), \
         patch("asyncio.run", side_effect=lambda c: asyncio.create_task(c)):

        generate_all_monthly_reports.run()
        generate_user_monthly_report.run(str(user.id))
        check_stale_connections.run()
        await asyncio.sleep(0.1)


def test_celery_app_config():
    assert celery_app.main == "savingstracker"
    assert "monthly-report-all-users" in celery_app.conf.beat_schedule
    for entry in celery_app.conf.beat_schedule.values():
        assert "description" not in entry
