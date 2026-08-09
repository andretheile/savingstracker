"""Security utilities — symmetric encryption for sensitive fields (bank credentials)."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from src.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazily initialise the Fernet cipher from the configured key."""
    global _fernet  # noqa: PLW0603
    if _fernet is None:
        if not settings.encryption_key:
            raise RuntimeError(
                "ENCRYPTION_KEY is not set. Generate one with:\n"
                '  python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        _fernet = Fernet(settings.encryption_key.encode())
    return _fernet


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string field and return the ciphertext as a UTF-8 string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a ciphertext string back to plaintext."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt field — invalid token or corrupted data")
        raise ValueError("Decryption failed. The encryption key may have changed.")
