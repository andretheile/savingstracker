"""Per-household Telegram and OpenRouter secrets, with env fallback."""

from __future__ import annotations

from src.config import settings
from src.core.security import decrypt_field, encrypt_field
from src.users.models import User


def _decrypt(ciphertext: str | None) -> str:
    if not ciphertext:
        return ""
    try:
        return decrypt_field(ciphertext)
    except (ValueError, RuntimeError):
        return ""


def telegram_token_for_user(user: User) -> str:
    return _decrypt(user.telegram_bot_token_encrypted) or (settings.telegram_bot_token or "")


def openrouter_for_user(user: User) -> tuple[str, str]:
    key = _decrypt(user.openrouter_api_key_encrypted) or (settings.openrouter_api_key or "")
    model = (user.openrouter_model or "").strip() or settings.openrouter_model
    return key, model


def set_telegram_token(user: User, token: str, username: str | None = None, name: str | None = None) -> None:
    user.telegram_bot_token_encrypted = encrypt_field(token)
    if username is not None:
        user.telegram_bot_username = username
    if name is not None:
        user.telegram_bot_name = name


def set_openrouter_key(user: User, api_key: str | None = None, model: str | None = None) -> None:
    if api_key:
        user.openrouter_api_key_encrypted = encrypt_field(api_key)
    if model is not None:
        user.openrouter_model = model


def copy_legacy_secrets_if_empty(user: User) -> None:
    """On first claim of the existing household, copy global .env secrets onto the user."""
    if not user.telegram_bot_token_encrypted and settings.telegram_bot_token:
        user.telegram_bot_token_encrypted = encrypt_field(settings.telegram_bot_token)
    if not user.openrouter_api_key_encrypted and settings.openrouter_api_key:
        user.openrouter_api_key_encrypted = encrypt_field(settings.openrouter_api_key)
    if not user.openrouter_model and settings.openrouter_model:
        user.openrouter_model = settings.openrouter_model
    if not user.telegram_allowed_user_ids and settings.telegram_allowed_user_ids:
        user.telegram_allowed_user_ids = settings.telegram_allowed_user_ids
    if not user.telegram_allowed_chat_ids and settings.telegram_allowed_chat_ids:
        user.telegram_allowed_chat_ids = settings.telegram_allowed_chat_ids
