# syntax=docker/dockerfile:1
FROM python:3.12.8-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.6.2
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src src
RUN uv sync --frozen --no-dev

FROM python:3.12.8-slim-bookworm AS runner
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH
WORKDIR /app

RUN groupadd --system --gid 10001 transitpulse \
    && useradd --system --uid 10001 --gid transitpulse --create-home transitpulse

COPY --from=builder --chown=transitpulse:transitpulse /app/.venv /app/.venv
COPY --chown=transitpulse:transitpulse src src
COPY --chown=transitpulse:transitpulse alembic.ini ./
COPY --chown=transitpulse:transitpulse migrations migrations

USER transitpulse
EXPOSE 8000
CMD ["uvicorn", "transitpulse.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
