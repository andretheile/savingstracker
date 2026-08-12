"""OpenRouter chat-completions client (OpenAI-compatible tool calling)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": model or settings.openrouter_model,
        "messages": messages,
        "temperature": 0.2,
        "include_reasoning": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://savingstracker.local",
                "X-Title": "SavingsTracker",
            },
            json=payload,
        )
        if response.status_code >= 400:
            logger.error("OpenRouter error %s: %s", response.status_code, response.text[:500])
            raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices")
    return choices[0].get("message") or {}


async def validate_api_key(api_key: str) -> None:
    """Raise ValueError if OpenRouter rejects the key."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    if response.status_code in (401, 403):
        raise ValueError("OpenRouter rejected the API key")
    if response.status_code >= 400:
        raise ValueError(f"OpenRouter HTTP {response.status_code}")
