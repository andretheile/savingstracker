"""Tool-calling agent loop over OpenRouter."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.openrouter import chat_completion
from src.llm.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8
MAX_HISTORY = 16

_history: dict[str, list[dict[str, Any]]] = defaultdict(list)

TOOL_LABELS = {
    "get_overview": "Getting a household overview",
    "list_accounts": "Listing accounts",
    "set_household_account": "Updating household accounts",
    "list_transactions": "Searching transactions",
    "add_transaction": "Adding a transaction",
    "set_transaction_category": "Changing a category",
    "set_transaction_exclude": "Updating an exclude flag",
    "list_categories": "Listing categories",
    "get_balance_sheet": "Reading the balance sheet",
    "get_kpis": "Evaluating KPIs",
    "create_kpi": "Creating a KPI",
    "validate_kpi_formula": "Checking a KPI formula",
    "get_projection": "Running the savings projection",
    "update_projection_config": "Updating projection settings",
    "reclassify_transactions": "Re-running auto-classification",
    "sync_bank": "Refreshing bank data",
    "confirm_bank_sync": "Finishing bank sync after app approval",
}


def _system_prompt(channel: str) -> str:
    brevity = (
        "Be concise; this is Telegram. Short lists, no markdown tables."
        if channel == "telegram"
        else (
            "Be concise. Use markdown (headings, lists, bold, short tables) when it helps. "
            "Do not wrap the whole answer in a code block."
        )
    )
    return (
        "You are the SavingsTracker assistant for a personal finance app. "
        f"Today is {date.today().isoformat()}. Currency is EUR.\n"
        "You can read and change the same data as the web app via tools. "
        "Household totals use accounts marked household (typically the joint giro ending 1121). "
        "Personal accounts are separate.\n"
        "Rules:\n"
        "- Always use tools for numbers. Do not invent balances or transactions.\n"
        "- Expenses are negative amounts when adding transactions.\n"
        f"- {brevity}\n"
        "- Never ask for a bank PIN or TAN. Sync uses the PIN stored encrypted when the bank was linked.\n"
        "- If sync_bank returns needs_approval, tell the user to confirm in the DKB app, then wait for them to say they did before calling confirm_bank_sync.\n"
        "- If a tool returns missing_pin, tell them to link the bank once more in Banking → Link account.\n"
        "- If a tool returns an error, explain it and suggest a fix.\n"
        "- After changing data, say what you changed."
    )


def clear_history(chat_id: int | str) -> None:
    _history.pop(str(chat_id), None)


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _extract_reasoning(message: dict[str, Any]) -> str:
    for key in ("reasoning", "reasoning_content"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    details = message.get("reasoning_details") or []
    parts: list[str] = []
    for item in details:
        if isinstance(item, str) and item.strip():
            parts.append(item.strip())
        elif isinstance(item, dict):
            text = item.get("text") or item.get("content") or ""
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def major_thinking_points(text: str, limit: int = 4) -> list[str]:
    """Keep a few short reasoning beats, not the full chain of thought."""
    text = (text or "").strip()
    if not text:
        return []
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", text) if block.strip()]
    if len(blocks) == 1:
        blocks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", blocks[0]) if part.strip()]
    points: list[str] = []
    for block in blocks:
        compact = " ".join(block.split())
        if len(compact) < 20:
            continue
        if len(compact) > 180:
            compact = compact[:177].rsplit(" ", 1)[0] + "…"
        points.append(compact)
        if len(points) >= limit:
            break
    return points


def _summarize_tool_result(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:160]
    if isinstance(data, dict) and data.get("error"):
        return f"Error: {data['error']}"
    if isinstance(data, list):
        return f"{len(data)} items"
    if isinstance(data, dict):
        if "count" in data:
            return f"{data['count']} matches"
        if "updated" in data:
            return f"{data['updated']} updated"
        if data.get("status") == "needs_approval":
            return "Waiting for DKB app approval"
        if data.get("status") == "synced":
            return data.get("message") or "Bank synced"
        if data.get("status") == "missing_pin":
            return "PIN not stored yet"
        if data.get("status") == "no_connection":
            return "No bank linked"
        if "name" in data and "household" in data:
            flag = "household" if data["household"] else "personal"
            return f"{data['name']} → {flag}"
        if "net_cashflow" in data:
            return f"Net {data['net_cashflow']}"
        if "projected_real" in data:
            return f"Real projection {data['projected_real']}"
        if data.get("excluded") is True:
            return "Excluded from totals"
        if data.get("category"):
            return f"Category: {data['category']}"
    return "Done"


def _compact_args(args: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in args.items():
        if value is None or value == "":
            continue
        compact[key] = value
    return compact


async def iter_agent_events(
    session: AsyncSession,
    user_id: uuid.UUID,
    user_text: str,
    chat_id: int | str,
    channel: str = "telegram",
    api_key: str | None = None,
    model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    key = str(chat_id)
    history = _history[key]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt(channel)},
        *history,
        {"role": "user", "content": user_text},
    ]

    final_text = ""
    for _ in range(MAX_TOOL_ROUNDS):
        message = await chat_completion(messages, tools=TOOL_DEFINITIONS, api_key=api_key, model=model)
        tool_calls = message.get("tool_calls") or []
        content = (message.get("content") or "").strip()
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.get("content") or "",
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        for extra in ("reasoning", "reasoning_content", "reasoning_details"):
            if message.get(extra):
                assistant_msg[extra] = message[extra]
        messages.append(assistant_msg)

        points = major_thinking_points(_extract_reasoning(message))
        if points:
            for point in points:
                yield {"type": "thinking", "content": point}
        elif tool_calls:
            first = (tool_calls[0].get("function") or {}).get("name") or ""
            yield {
                "type": "thinking",
                "content": TOOL_LABELS.get(first, f"Using {first}" if first else "Working"),
            }

        if not tool_calls:
            final_text = content
            break

        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            args = _parse_arguments(fn.get("arguments"))
            logger.info("LLM tool %s(%s)", name, args)
            yield {
                "type": "tool",
                "name": name,
                "label": TOOL_LABELS.get(name, name),
                "arguments": _compact_args(args),
                "status": "running",
            }
            result = await execute_tool(session, user_id, name, args)
            summary = _summarize_tool_result(result)
            yield {
                "type": "tool_result",
                "name": name,
                "label": TOOL_LABELS.get(name, name),
                "summary": summary,
                "status": "error" if summary.startswith("Error:") else "done",
            }
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or name,
                    "name": name,
                    "content": result,
                }
            )
        final_text = content
    else:
        if not final_text:
            final_text = "I hit the tool-call limit. Try a more specific question."

    if not final_text:
        final_text = "Done."

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": final_text})
    del history[:-MAX_HISTORY]
    yield {"type": "reply", "content": final_text}


async def run_agent(
    session: AsyncSession,
    user_id: uuid.UUID,
    user_text: str,
    chat_id: int | str,
    channel: str = "telegram",
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    reply = "Done."
    async for event in iter_agent_events(
        session, user_id, user_text, chat_id, channel, api_key=api_key, model=model
    ):
        if event.get("type") == "reply":
            reply = event["content"]
    return reply
