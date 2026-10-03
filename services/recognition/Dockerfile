# services/recognition/Dockerfile
# Build stage - use Python slim base (CUDA base only needed for local ONNX GPU)
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for opencv and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Enable uv cache
ENV UV_CACHE_DIR=/root/.cache/uv

# Copy dependency files first for better cache
COPY pyproject.toml uv.lock ./

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-cache --prefix=/install -r pyproject.toml

# Runtime stage - Python slim for production
FROM python:3.12-slim AS runner

WORKDIR /app

ARG PORT=8001
ARG WORKERS=2

# Install runtime dependencies for OpenCV, Tesseract
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 libgomp1 \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Copy installed packages from builder
COPY --from=builder --chown=app:app /install /usr/local

# Copy application code
COPY --chown=app:app recognition_app ./app

# Install gunicorn for production
RUN pip3 install --no-cache-dir gunicorn

USER app
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use gunicorn with workers for production (2 workers for ML workloads)
CMD ["gunicorn", "app.main:app", "--workers", "${WORKERS}", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT}", "--timeout", "120", "--keep-alive", "5"]