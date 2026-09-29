# PokéX — Pokémon TCG Monorepo

Monorepo for Pokémon TCG card data ingestion, recognition, scraping, and web/desktop apps.

## Architecture

```
pokex/
├── apps/
│   ├── web/                    # Vite + React + TypeScript (port 3000)
│   └── desktop-mobile/         # Tauri + React + Rust (port 8000 API)
├── services/
│   ├── data-ingestion/         # FastAPI + PostgreSQL + MinIO (port 8000)
│   ├── recognition/            # FastAPI + YOLOv8 ONNX + EasyOCR (port 8001)
│   └── scraper/                # FastAPI + JustTCG API (port 8002)
├── test/
│   ├── python/                 # Unit tests (cache, HTTP, Redis)
│   ├── e2e/                    # Integration tests (full cache flow)
│   ├── web/                    # Playwright + Vitest (React Query)
│   └── desktop/                # Rust tests (moka cache, sync)
├── docker-compose.yml          # 12 services
└── .github/workflows/ci.yml    # CI: lint, typecheck, build, test
```

## Services

| Service | Port | Stack | Purpose |
|---------|------|-------|---------|
| data-ingestion | 8000 | FastAPI, SQLAlchemy, PostgreSQL, MinIO | CRUD for sets, cards, prices; image upload |
| recognition | 8001 | FastAPI, ONNXRuntime, OpenCV, pytesseract | YOLOv8 card detection + OCR fallback |
| scraper | 8002 | FastAPI, httpx | Sync sets/cards/prices from JustTCG API |
| web | 3000 | Vite, React 19, TanStack Query, Tailwind v4 | Browser app (Sets, Scan, Collection) |
| desktop-mobile | — | Tauri, React, Rust (libsql/SQLite) | Offline-first desktop/mobile app |

## Quick Start

```bash
# Prerequisites: Docker Desktop, pnpm, Rust (for desktop)

# 1. Start infrastructure (PostgreSQL, Redis, MinIO, etc.)
docker compose up -d postgres redis minio

# 2. Build & start all services
docker compose up -d --build data-ingestion scraper recognition web

# 3. Or run locally (Python services)
cd services/data-ingestion && python -m uvicorn app.main:app --reload --port 8000
cd services/recognition && python -m uvicorn app.main:app --reload --port 8001
cd services/scraper && python -m uvicorn app.main:app --reload --port 8002

# 4. Web app
cd apps/web && pnpm install && pnpm dev
```

## Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required
JUSTTCG_API_KEY=your_api_key
DATABASE_URL=postgresql+asyncpg://pokeuser:pokepass@localhost:5432/pokedb
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=pokemon-cards

# Optional
NEXT_PUBLIC_RECOGNITION_URL=http://localhost:8001
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_RECOGNITION_URL=http://localhost:8001
```

## Testing

```bash
# Python (all services)
cd D:\github\pokex
test-env\Scripts\python.exe -m pytest test/python/ test/e2e/ -v

# Web (Playwright)
cd apps/web && pnpm playwright test

# Desktop (Rust)
cd apps/desktop-mobile/src-tauri && cargo test
```

## CI Pipeline

`.github/workflows/ci.yml` runs on PR/push:
- `lint` — biome (JS/TS), ruff (Python)
- `typecheck` — tsc, mypy
- `build` — vite build, cargo build, Docker images
- `test-python` — pytest (48 tests)
- `test-web` — Playwright
- `test-desktop` — cargo test (12 tests)
- `test-e2e` — full cache flow with Redis

## Key Patterns

- **Caching**: Cache-Control/ETag middleware (data-ingestion), moka TTL cache (desktop API URL), React Query (web)
- **Sync**: Desktop has full/incremental sync managers with SQLite; scraper pulls from JustTCG to PostgreSQL
- **Types**: Inlined in each app (no shared package); recognition types duplicated across Python/Rust
- **Database**: PostgreSQL (data-ingestion), SQLite/libsql (desktop), Redis (cache/invalidation)
- **Observability**: OTel collector, Jaeger, Prometheus, Loki in docker-compose

## Docker Build

```bash
docker build -t pokex-web apps/web
docker build -t pokex-data-ingestion services/data-ingestion
docker build -t pokex-recognition services/recognition
docker build -t pokex-scraper services/scraper
```

All images use `uv` for Python deps, pinned base images, BuildKit cache mounts.