"""FastAPI main entrypoint with lifecycle management for DB, Redis, Telegram Bot, and Web Dashboard."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.accounts.router import router as accounts_router
from src.balance_sheets.router import router as balance_sheets_router
from src.classification.service import seed_default_categories
from src.config import settings
from src.core.cache import close_redis
from src.core.database import dispose_engine, get_standalone_session
from src.kpis.router import router as kpis_router
from src.kpis.service import ensure_builtin_kpis_seeded
from src.projections.router import router as projections_router
from src.telegram_bot.bot import create_telegram_bot
from src.transactions.router import router as transactions_router
from src.users.router import router as users_router

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    logger.info("Initializing SavingsTracker application...")

    # 1. Seed database with default categories and KPIs
    async with get_standalone_session() as session:
        await seed_default_categories(session)
        await ensure_builtin_kpis_seeded(session)

    # 2. Initialize Telegram bot if token is configured
    bot_app = create_telegram_bot()
    if bot_app:
        await bot_app.initialize()
        await bot_app.start()
        if bot_app.updater:
            await bot_app.updater.start_polling()
        logger.info("Telegram bot polling started.")

    yield

    # Shutdown sequence
    logger.info("Shutting down SavingsTracker application...")
    if bot_app:
        if bot_app.updater:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
    await close_redis()
    await dispose_engine()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="SavingsTracker API & Web Dashboard",
    description="Modular personal finance backend with custom KPIs, bank connections, projections, and web dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register REST API routers under /api prefix
app.include_router(users_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(kpis_router, prefix="/api")
app.include_router(projections_router, prefix="/api")
app.include_router(balance_sheets_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "savingstracker"}


# Mount static frontend build if dist folder exists
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
