"""Telegram pairing codes and bot identity (in-memory, single-user)."""

from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass

_CODE_TTL_SECONDS = 600


@dataclass
class LinkCode:
    code: str
    user_id: uuid.UUID
    expires_at: float


_codes: dict[str, LinkCode] = {}
_bot_username: str | None = None
_bot_name: str | None = None


def set_bot_identity(username: str | None, name: str | None = None) -> None:
    global _bot_username, _bot_name
    _bot_username = username
    _bot_name = name


def get_bot_username() -> str | None:
    return _bot_username


def get_bot_name() -> str | None:
    return _bot_name


def create_link_code(user_id: uuid.UUID) -> LinkCode:
    _purge_expired()
    code = secrets.token_hex(3).upper()
    entry = LinkCode(code=code, user_id=user_id, expires_at=time.time() + _CODE_TTL_SECONDS)
    _codes[code] = entry
    return entry


def consume_link_code(code: str) -> uuid.UUID | None:
    _purge_expired()
    entry = _codes.pop(code.strip().upper(), None)
    if entry is None or entry.expires_at < time.time():
        return None
    return entry.user_id


def deep_link_for(code: str, username: str | None = None) -> str | None:
    bot = username or _bot_username
    if not bot:
        return None
    return f"https://t.me/{bot}?start={code}"


def _purge_expired() -> None:
    now = time.time()
    expired = [key for key, val in _codes.items() if val.expires_at < now]
    for key in expired:
        _codes.pop(key, None)
