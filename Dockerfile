# ── Build stage ────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./

# Install dependencies into a virtual env
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r pyproject.toml

# ── Runtime stage ──────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/

EXPOSE 8000

# Default: run API + Telegram bot
CMD ["python", "-m", "src.main"]
