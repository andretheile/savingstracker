"""HTTP chat endpoint for the OpenRouter finance agent."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.database import get_standalone_session
from src.core.dependencies import get_db
from src.llm.agent import clear_history, iter_agent_events
from src.users.service import get_or_create_default_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class LLMStatusResponse(BaseModel):
    configured: bool
    model: str | None = None


def _web_history_key(user_id: uuid.UUID) -> str:
    return f"web:{user_id}"


@router.get("/status", response_model=LLMStatusResponse)
async def llm_status():
    configured = bool(settings.openrouter_api_key)
    return LLMStatusResponse(
        configured=configured,
        model=settings.openrouter_model if configured else None,
    )


@router.post("/chat")
async def llm_chat(data: ChatRequest):
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set an OpenRouter API key first.",
        )
    text = data.message.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is empty.",
        )

    async def event_stream():
        try:
            async with get_standalone_session() as session:
                user = await get_or_create_default_user(session)
                async for event in iter_agent_events(
                    session,
                    user.id,
                    text,
                    _web_history_key(user.id),
                    channel="web",
                ):
                    yield f"data: {json.dumps(event, default=str)}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
        except Exception:
            logger.exception("Web LLM chat failed")
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "detail": (
                            "The language model request failed. "
                            "Check the OpenRouter key and try again."
                        ),
                    }
                )
                + "\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/reset")
async def llm_reset(db: AsyncSession = Depends(get_db)):
    user = await get_or_create_default_user(db)
    clear_history(_web_history_key(user.id))
    return {"ok": True}
