"""Async database engine, session factory, and dependency provider."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

engine_kwargs = {"echo": settings.debug}
if "sqlite" in settings.database_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session, auto-closes on exit."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_standalone_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use outside FastAPI (Celery tasks, scripts)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ensure_schema() -> None:
    """Add columns that create_all will not apply to an existing SQLite file."""
    from sqlalchemy import inspect, text

    async with engine.begin() as conn:

        def column_names(sync_conn, table: str) -> set[str]:
            insp = inspect(sync_conn)
            if not insp.has_table(table):
                return set()
            return {c["name"] for c in insp.get_columns(table)}

        cols = await conn.run_sync(lambda c: column_names(c, "transactions"))
        if cols and "exclude_from_totals" not in cols:
            await conn.execute(
                text(
                    "ALTER TABLE transactions ADD COLUMN exclude_from_totals "
                    "BOOLEAN DEFAULT 0 NOT NULL"
                )
            )

        acc_cols = await conn.run_sync(lambda c: column_names(c, "accounts"))
        if acc_cols and "include_in_household" not in acc_cols:
            await conn.execute(
                text(
                    "ALTER TABLE accounts ADD COLUMN include_in_household "
                    "BOOLEAN DEFAULT 1 NOT NULL"
                )
            )
        if acc_cols and "is_depot" not in acc_cols:
            await conn.execute(
                text(
                    "ALTER TABLE accounts ADD COLUMN is_depot "
                    "BOOLEAN DEFAULT 0 NOT NULL"
                )
            )

        bank_cols = await conn.run_sync(lambda c: column_names(c, "bank_connections"))
        if bank_cols and "pin_encrypted" not in bank_cols:
            await conn.execute(
                text("ALTER TABLE bank_connections ADD COLUMN pin_encrypted TEXT")
            )

        user_cols = await conn.run_sync(lambda c: column_names(c, "users"))
        user_alters = {
            "telegram_bot_token_encrypted": "TEXT",
            "telegram_bot_username": "VARCHAR(255)",
            "telegram_bot_name": "VARCHAR(255)",
            "telegram_allowed_user_ids": "VARCHAR(512) DEFAULT '' NOT NULL",
            "telegram_allowed_chat_ids": "VARCHAR(512) DEFAULT '' NOT NULL",
            "openrouter_api_key_encrypted": "TEXT",
            "openrouter_model": "VARCHAR(128)",
        }
        for col, ddl in user_alters.items():
            if user_cols and col not in user_cols:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))


async def dispose_engine() -> None:
    """Gracefully close all connections on shutdown."""
    await engine.dispose()
