"""Read/write KEY=value lines in the project .env file."""

from __future__ import annotations

import re
from pathlib import Path

from src.config import settings

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def persist_env_value(key: str, value: str) -> None:
    """Update or append KEY=value in .env and on the live Settings object."""
    line = f"{key}={value}"
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if _ENV_PATH.exists():
        text = _ENV_PATH.read_text()
        if pattern.search(text):
            _ENV_PATH.write_text(pattern.sub(line, text))
        else:
            suffix = "" if text.endswith("\n") else "\n"
            _ENV_PATH.write_text(f"{text}{suffix}{line}\n")
    else:
        _ENV_PATH.write_text(f"{line}\n")
    attr = key.lower()
    if hasattr(settings, attr):
        setattr(settings, attr, value)
