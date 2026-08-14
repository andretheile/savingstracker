"""FastAPI main entrypoint with lifecycle management for DB, Redis, Telegram Bot, and Web Dashboard."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import src.accounts.models  # noqa
import src.auth.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.kpis.models  # noqa
import src.projections.models  # noqa
import src.scheduler.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.accounts.router import router as accounts_router
from src.accounts.service import apply_default_household_selection
from src.auth.dependencies import get_current_user
from src.auth.router import api_router as auth_api_router
from src.auth.router import household_router
from src.auth.router import pages_router as auth_pages_router
from src.balance_sheets.router import router as balance_sheets_router
from src.banking.router import router as banking_router
from src.classification.service import reclassify_all_users, seed_default_categories
from src.config import settings
from src.core.base_model import Base
from src.core.cache import close_redis
from src.core.database import dispose_engine, engine, ensure_schema, get_standalone_session
from src.kpis.router import router as kpis_router
from src.kpis.service import ensure_builtin_kpis_seeded
from src.llm.router import router as llm_router
from src.projections.router import router as projections_router
from src.telegram_bot.bot import start_all_household_bots, stop_polling
from src.telegram_bot.router import router as telegram_router
from src.transactions.router import router as transactions_router
from src.users.router import router as users_router

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema()

    async with get_standalone_session() as session:
        await seed_default_categories(session)
        await ensure_builtin_kpis_seeded(session)
        await apply_default_household_selection(session)
        classified = await reclassify_all_users(session)
        if classified:
            logger.info("Auto-classified %d existing transactions", classified)

    try:
        await start_all_household_bots()
    except Exception:
        logger.exception("Telegram bots failed to start")

    yield

    logger.info("Shutting down SavingsTracker application...")
    await stop_polling()
    await close_redis()
    await dispose_engine()
    logger.info("Shutdown complete.")


_docs = "/docs" if settings.debug else None
_redoc = "/redoc" if settings.debug else None

app = FastAPI(
    title="SavingsTracker API & Web Dashboard",
    description="Modular personal finance backend with custom KPIs, bank connections, projections, and web dashboard.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs,
    redoc_url=_redoc,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.auth_secret_key or "dev-only-change-me",
    https_only=bool(settings.public_base_url.startswith("https://")),
    same_site="lax",
    max_age=14 * 24 * 3600,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.include_router(auth_pages_router)
app.include_router(auth_api_router, prefix="/api")
app.include_router(household_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(users_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(accounts_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(banking_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(transactions_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(kpis_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(projections_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(balance_sheets_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(telegram_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(llm_router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "savingstracker"}


frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path in {"login", "auth/callback", "logout"}:
            return FileResponse(frontend_dist / "index.html")
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
