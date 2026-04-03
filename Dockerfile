# === Build Stage ===
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Install dependencies first (layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy backend source
COPY backend/ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# === Runtime Stage ===
FROM python:3.13-slim-bookworm

WORKDIR /app

COPY --from=builder /app /app
COPY knowledge/ ./knowledge/

ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --create-home app && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
