"""Free-text Telegram chat routed through the OpenRouter LLM agent."""

from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ContextTypes

from src.core.database import get_standalone_session
from src.llm.agent import clear_history, run_agent
from src.telegram_bot.handlers.common import (
    authorize_telegram_user,
    household_id_from_context,
    is_group_chat,
)
from src.telegram_bot.linking import get_bot_username
from src.users.credentials import openrouter_for_user

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4000

NO_LLM_KEY = (
    "Chat needs an OpenRouter API key.\n\n"
    "Open SavingsTracker → Settings → paste a key from openrouter.ai, then try again."
)


def split_telegram(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return chunks


def bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    username = getattr(context.bot, "username", None) or get_bot_username() or ""
    if not isinstance(username, str):
        return ""
    return username.lstrip("@")


def strip_bot_mention(text: str, username: str) -> str:
    if not username:
        return text.strip()
    cleaned = re.sub(rf"@{re.escape(username)}\b", "", text, flags=re.IGNORECASE)
    return " ".join(cleaned.split())


def bot_was_addressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """True when this is a DM, a @mention of the bot, or a reply to the bot."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return False
    if chat.type == ChatType.PRIVATE:
        return True

    bot_id = getattr(context.bot, "id", None)
    reply = message.reply_to_message
    if reply is not None and reply.from_user is not None and reply.from_user.id == bot_id:
        return True

    username = bot_username(context).lower()
    text = message.text or ""
    if username and f"@{username}" in text.lower():
        return True

    for entity in message.entities or []:
        entity_type = getattr(entity, "type", "")
        if entity_type == "mention" and username:
            mention = _entity_text(message, entity).lstrip("@").lower()
            if mention == username:
                return True
        if entity_type == "text_mention":
            mentioned = getattr(entity, "user", None)
            if mentioned is not None and mentioned.id == bot_id:
                return True
    return False


def _entity_text(message, entity) -> str:
    parse = getattr(message, "parse_entity", None)
    if callable(parse):
        try:
            return parse(entity) or ""
        except Exception:
            pass
    text = message.text or ""
    start = getattr(entity, "offset", 0)
    length = getattr(entity, "length", 0)
    return text[start : start + length]


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_chat:
        return
    if not bot_was_addressed(update, context):
        if is_group_chat(update):
            logger.info(
                "Ignoring group message without @%s mention or reply",
                bot_username(context) or "bot",
            )
        return

    raw = (update.effective_message.text or "").strip()
    text = strip_bot_mention(raw, bot_username(context))
    if not text:
        await update.effective_message.reply_text(
            "Ask me about spending, or reply to this message with a question."
        )
        return

    user = await authorize_telegram_user(update, household_id_from_context(context))
    if user is None:
        return

    api_key, model = openrouter_for_user(user)
    if not api_key:
        await update.effective_message.reply_text(NO_LLM_KEY)
        return

    if is_group_chat(update) and update.effective_user:
        speaker = update.effective_user.first_name or update.effective_user.username or "Someone"
        prompt = f"{speaker}: {text}"
    else:
        prompt = text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        async with get_standalone_session() as session:
            reply = await run_agent(
                session,
                user.id,
                prompt,
                update.effective_chat.id,
                channel="telegram",
                api_key=api_key,
                model=model,
            )
    except Exception:
        logger.exception("LLM chat failed")
        await update.effective_message.reply_text(
            "The language model request failed. Check the OpenRouter key and try again."
        )
        return

    for chunk in split_telegram(reply):
        await update.effective_message.reply_text(chunk)


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_chat:
        return
    user = await authorize_telegram_user(update, household_id_from_context(context))
    if user is None:
        return
    clear_history(update.effective_chat.id)
    await update.effective_message.reply_text("Chat history cleared.")
