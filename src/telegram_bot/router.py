"""FastAPI router for Telegram bot status, pairing, and token setup."""

from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot

from src.auth.dependencies import CurrentUser
from src.core.dependencies import get_db
from src.llm.openrouter import validate_api_key
from src.telegram_bot.bot import start_polling_for_user, validate_bot_token
from src.telegram_bot.linking import create_link_code, deep_link_for
from src.users.credentials import (
    openrouter_for_user,
    set_openrouter_key,
    set_telegram_token,
    telegram_token_for_user,
)
from src.users.service import unlink_telegram

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramStatusResponse(BaseModel):
    bot_configured: bool
    bot_running: bool
    bot_username: str | None = None
    bot_name: str | None = None
    connected: bool
    telegram_id: int | None = None
    next_digest: str
    llm_configured: bool = False
    llm_model: str | None = None


class TelegramTokenRequest(BaseModel):
    token: str


class TelegramLinkResponse(BaseModel):
    code: str
    deep_link: str | None
    expires_in: int = 600
    bot_username: str | None = None


def _next_digest_label() -> str:
    today = date.today()
    nxt = (today.replace(day=1) + relativedelta(months=1)).replace(day=1)
    return nxt.strftime("%d %b %Y").lstrip("0")


@router.get("/status", response_model=TelegramStatusResponse)
async def telegram_status(user: CurrentUser):
    from src.telegram_bot.bot import bot_is_running_for_user

    token = telegram_token_for_user(user)
    llm_key, llm_model = openrouter_for_user(user)
    return TelegramStatusResponse(
        bot_configured=bool(token),
        bot_running=bot_is_running_for_user(user.id),
        bot_username=user.telegram_bot_username,
        bot_name=user.telegram_bot_name,
        connected=user.telegram_id is not None,
        telegram_id=user.telegram_id,
        next_digest=_next_digest_label(),
        llm_configured=bool(llm_key),
        llm_model=llm_model if llm_key else None,
    )


@router.post("/token")
async def set_telegram_token_endpoint(
    data: TelegramTokenRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    token = data.token.strip()
    if not token or ":" not in token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That does not look like a BotFather token.",
        )
    try:
        username = await validate_bot_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Telegram rejected the token: {exc}",
        ) from exc

    set_telegram_token(user, token, username=username)
    await db.flush()
    try:
        await start_polling_for_user(user.id, token, username=username)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token is valid but polling failed to start: {exc}",
        ) from exc
    return {"ok": True, "bot_username": username}


@router.post("/link", response_model=TelegramLinkResponse)
async def create_telegram_link(user: CurrentUser):
    if not telegram_token_for_user(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set a Telegram bot token first.",
        )
    entry = create_link_code(user.id)
    return TelegramLinkResponse(
        code=entry.code,
        deep_link=deep_link_for(entry.code, user.telegram_bot_username),
        bot_username=user.telegram_bot_username,
    )


@router.post("/unlink")
async def unlink_telegram_account(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await unlink_telegram(db, user.id)
    return {"ok": True}


@router.post("/test")
async def send_test_message(user: CurrentUser):
    token = telegram_token_for_user(user)
    if not user.telegram_id or not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram is not connected yet.",
        )
    bot = Bot(token=token)
    await bot.send_message(
        chat_id=user.telegram_id,
        text=(
            "SavingsTracker is linked. You will get the household digest on the 1st of each month. "
            "Try /balance, /kpis, or just ask a question."
        ),
    )
    return {"ok": True}


class LLMConfigRequest(BaseModel):
    api_key: str = ""
    model: str | None = None


@router.post("/llm")
async def set_llm_config(
    data: LLMConfigRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    key = data.api_key.strip()
    current_key, current_model = openrouter_for_user(user)
    model = (data.model or "").strip() or current_model

    if not key and not current_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paste an OpenRouter API key.",
        )

    if key:
        if len(key) < 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That does not look like an OpenRouter API key.",
            )
        try:
            await validate_api_key(key)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        set_openrouter_key(user, api_key=key, model=model)
    else:
        set_openrouter_key(user, model=model)
    await db.flush()
    _, saved_model = openrouter_for_user(user)
    return {"ok": True, "model": saved_model}
