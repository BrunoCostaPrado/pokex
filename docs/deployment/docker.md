# Docker Deployment

## Image Architecture

All services use multi-stage Docker builds:

- Build stage: uv (Python), pnpm + Vite (Node), Cargo (Rust)
- Runtime stage: minimal base (Alpine or Debian slim)
- BuildKit cache mounts for dependency layers
- Non-root user in runtime
- Health checks for orchestration

---

## Data Ingestion Dockerfile

```dockerfile
# services/data-ingestion/Dockerfile
# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_CACHE_DIR=/root/.cache/uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-cache --prefix=/install -r pyproject.toml

# Runtime stage
FROM python:3.12-alpine AS runner
WORKDIR /app
RUN apk add --no-cache ca-certificates \
    && adduser -D -s /bin/bash app

COPY --from=builder --chown=app:app /install /usr/local
COPY --chown=app:app data_ingestion_app ./app

# Gunicorn for production
RUN pip install --no-cache-dir gunicorn

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget -q --spider http://localhost:8000/health || exit 1

CMD ["gunicorn", "app.main:app", "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5"]
```

What matters here:
- uv for fast, cached dependency install
- Alpine runtime (~50MB base)
- Gunicorn with 4 Uvicorn workers
- Health check hits `/health` endpoint

---

## Recognition Dockerfile

```dockerfile
# services/recognition/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_CACHE_DIR=/root/.cache/uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-cache --prefix=/install -r pyproject.toml

# Runtime - needs OpenCV system deps
FROM python:3.12-slim AS runner
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" app

COPY --from=builder --chown=app:app /install /usr/local
COPY --chown=app:app recognition_app ./app

RUN pip install --no-cache-dir gunicorn

USER app
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -q --spider http://localhost:8001/health || exit 1

CMD ["gunicorn", "app.main:app", "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8001", "--timeout", "300", "--keep-alive", "5"]
```

What matters:
- Slim (not Alpine) for OpenCV compatibility
- System deps for OpenCV/EasyOCR
- 2 workers (CPU-intensive ONNX inference)
- Longer timeout (300s) for recognition requests

---

## Scraper Dockerfile

```dockerfile
# services/scraper/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_CACHE_DIR=/root/.cache/uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-cache --prefix=/install -r pyproject.toml

FROM python:3.12-alpine AS runner
WORKDIR /app
RUN apk add --no-cache ca-certificates \
    && adduser -D -s /bin/bash app

COPY --from=builder --chown=app:app /install /usr/local
COPY --chown=app:app scraper_app ./app

RUN pip install --no-cache-dir gunicorn

USER app
EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:8002/health || exit 1

CMD ["gunicorn", "app.main:app", "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8002", "--timeout", "120", "--keep-alive", "5"]
```

---

## Web Dockerfile

```dockerfile
# apps/web/Dockerfile
# Build stage
FROM node:22-alpine AS builder
WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable

# Copy all package files for proper workspace resolution
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
COPY apps/desktop-mobile/package.json apps/desktop-mobile/
COPY packages/ui/package.json packages/ui/

# Copy all source for workspace packages
COPY packages/ui packages/ui
COPY apps/web apps/web
COPY apps/desktop-mobile apps/desktop-mobile

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm approve-builds @biomejs/biome @swc/core esbuild msw --yes && \
    pnpm install --frozen-lockfile --prefer-offline

# Build @pokex/ui first, then web
RUN cd packages/ui && pnpm exec tsc && cd ../.. && pnpm run build --filter web

# Runtime stage
FROM nginx:alpine AS runner
WORKDIR /usr/share/nginx/html

# Copy built assets
COPY --from=builder /app/apps/web/dist .

# Copy nginx config (from root context)
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

# Non-root user (nginx user exists in nginx:alpine)
USER nginx

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

**Note:** Build context is repo root (`context = "."` in `docker-bake.hcl`). `apps/web/Dockerfile` paths resolved from root.

### Nginx Config (`apps/web/nginx.conf`)

```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://data-ingestion:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /recognition/ {
        proxy_pass http://recognition:8001/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Desktop-Mobile (Tauri)

Tauri builds native binaries, not Docker images. For CI:

```dockerfile
# Dockerfile.tauri (for CI only)
FROM ubuntu:22.04 AS builder
RUN apt-get update && apt-get install -y \
    libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev \
    patchelf libgtk-3-dev libayatana-appindicator3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

# Install Node/pnpm
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app
COPY . .
RUN pnpm install --frozen-lockfile
RUN cd apps/desktop-mobile && pnpm tauri build
```

---

## Docker Compose (Production)

```yaml
# docker-compose.prod.yml
x-common-env: &common-env
  DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
  REDIS_URL: redis://redis:6379
  MINIO_ENDPOINT: minio:9000
  MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
  MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
  MINIO_SECURE: "false"
  MINIO_BUCKET: pokemon-cards

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 1G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 10s

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    deploy:
      resources:
        limits:
          memory: 512M

  minio:
    image: elestio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio-data:/data
    deploy:
      resources:
        limits:
          memory: 512M

  data-ingestion:
    image: ghcr.io/your-org/pokex-data-ingestion:latest
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
    environment:
      <<: *common-env
      IMAGE_STORAGE_PATH: /app/images
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
      redis:
        condition: service_healthy

  recognition:
    image: ghcr.io/your-org/pokex-recognition:latest
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
    environment:
      <<: *common-env
      PYTHONUNBUFFERED: "1"
      NIM_API_KEY: ${NVIDA}
    depends_on:
      minio:
        condition: service_healthy
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
      data-ingestion:
        condition: service_started

  scraper:
    image: ghcr.io/your-org/pokex-scraper:latest
    deploy:
      replicas: 1
    environment:
      <<: *common-env
      DATA_API_URL: http://data-ingestion:8000
      JUSTTCG_API_KEY: ${JUSTTCG_API_KEY}
    depends_on:
      - data-ingestion

  web:
    image: ghcr.io/your-org/pokex-web:latest
    deploy:
      replicas: 3
    ports:
      - "80:80"
    depends_on:
      - recognition

volumes:
  pgdata:
  redis-data:
  minio-data:
```

---

## Building Images

### Local Build

```bash
# Single image
docker build -t pokex-web apps/web
docker build -t pokex-data-ingestion services/data-ingestion
docker build -t pokex-recognition services/recognition
docker build -t pokex-scraper services/scraper

# Parallel with Buildx (multi-platform)
docker buildx bake -f docker-bake.hcl
```

### docker-bake.hcl

```hcl
# docker-bake.hcl
group "default" {
  targets = ["web", "data-ingestion", "recognition", "scraper"]
}

target "web" {
  context = "."
  tags = ["pokex-web"]
  dockerfile = "apps/web/Dockerfile"
}
# Context = root (".") so COPY apps/web/nginx.conf works.
# Python service contexts remain per-service directories.
```

target "data-ingestion" {
  context = "./services/data-ingestion"
  tags = ["pokex-data-ingestion"]
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
}

target "recognition" {
  context = "./services/recognition"
  tags = ["pokex-recognition"]
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64"]
}

target "scraper" {
  context = "./services/scraper"
  tags = ["pokex-scraper"]
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
}
```

### Multi-Platform Build

```bash
# Create builder
docker buildx create --name pokex-builder --use --bootstrap

# Build all
docker buildx bake -f docker-bake.hcl --push

# Or with tags
docker buildx bake -f docker-bake.hcl --push \
  --set "web.tags=ghcr.io/your-org/pokex-web:v1.0.0" \
  --set "data-ingestion.tags=ghcr.io/your-org/pokex-data-ingestion:v1.0.0" \
  ...
```

---

## Image Optimization

### Layer Caching

| Stage | Cache Key | Invalidated By |
|-------|-----------|----------------|
| Python deps | `uv-${hash(pyproject.toml,uv.lock)}` | Dependency changes |
| Node deps | `pnpm-${hash(pnpm-lock.yaml)}` | Dependency changes |
| Rust deps | `cargo-${hash(Cargo.lock)}` | Dependency changes |
| Source code | `source-${hash(src/)}` | Any source change |

### Size Optimization

| Image | Target Size | Techniques |
|-------|-------------|------------|
| data-ingestion | ~200MB | Alpine, uv prefix install, no dev deps |
| recognition | ~1.2GB | Slim (OpenCV), model baked in |
| scraper | ~180MB | Alpine, minimal deps |
| web | ~25MB | Nginx + static files only |

### Security Scanning

```bash
# Trivy scan
trivy image --severity HIGH,CRITICAL pokex-web:latest

# In CI
- name: Scan images
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'ghcr.io/your-org/pokex-*'
    severity: 'HIGH,CRITICAL'
```

---

## Environment Variables (Production)

```bash
# Required
POSTGRES_USER=pokeuser
POSTGRES_PASSWORD=strong-random-password
POSTGRES_DB=pokedb
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=strong-random-password
MINIO_BUCKET=pokemon-cards
JUSTTCG_API_KEY=your-production-key

# Optional
DATABASE_URL=postgresql+asyncpg://...  # Auto-constructed if not set
REDIS_URL=redis://redis:6379
MINIO_ENDPOINT=minio:9000
MINIO_SECURE=false
```

---

## Deployment Checklist

- [ ] All images built and pushed to registry
- [ ] `.env.prod` configured with strong secrets
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] MinIO bucket created with public read policy
- [ ] DNS configured for web/recognition endpoints
- [ ] TLS certificates provisioned (Let's Encrypt / cert-manager)
- [ ] Health checks passing on all services
- [ ] Monitoring alerts configured
- [ ] Backup strategy for PostgreSQL/MinIO