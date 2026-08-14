"""Keep unit tests off the developer/CI Postgres URL and encryption placeholder."""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ.setdefault("AUTH_SECRET_KEY", "test-auth-secret-not-for-prod")

import src.auth.models  # noqa: E402,F401
import src.users.models  # noqa: E402,F401
