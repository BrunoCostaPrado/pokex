# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app

# Enable uv cache
ENV UV_CACHE_DIR=/root/.cache/uv

# Copy dependency files first for better cache
COPY pyproject.toml uv.lock ./

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-cache --prefix=/install -r pyproject.toml

# Runtime stage
FROM python:3.12-alpine AS runner
WORKDIR /app

ARG PORT=8000
ARG WORKERS=4

# Install runtime dependencies and create user in single layer
RUN apk add --no-cache ca-certificates \
    && adduser -D -s /bin/bash app

# Copy installed packages and app with correct ownership
COPY --from=builder --chown=app:app /install /usr/local
COPY --chown=app:app data_ingestion_app ./app

# Install gunicorn for production
RUN pip install --no-cache-dir gunicorn

USER app
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget -q --spider http://localhost:${PORT}/health || exit 1

# Use gunicorn with workers for production
CMD ["gunicorn", "app.main:app", "--workers", "${WORKERS}", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT}", "--timeout", "120", "--keep-alive", "5"]