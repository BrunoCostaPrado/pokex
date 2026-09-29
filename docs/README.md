# PokéX Documentation

Documentation for the Pokémon TCG monorepo.

## Quick Navigation

| Category | Description |
|----------|-------------|
| [Architecture](architecture/) | System design, data flows, service boundaries |
| [API Reference](api/) | REST endpoints, schemas, authentication |
| [Development](development/) | Local setup, coding standards, testing |
| [Deployment](deployment/) | Docker, CI/CD, production hardening |
| [Contributing](contributing/) | Workflow, PR process, release process |

## Project Overview

PokéX is a monorepo for Pokémon TCG card data management:

- 3 Python microservices (FastAPI): Data Ingestion, Recognition, Scraper
- 2 React apps (Vite + React 19): Web (browser), Desktop-Mobile (Tauri/Rust)
- Shared UI package (`@pokex/ui`) with 10 reusable components
- Infrastructure: PostgreSQL, Redis, MinIO, observability stack

## Technology Stack

| Layer | Technologies |
|-------|--------------|
| Frontend | React 19, TypeScript, Vite, TanStack Query, Tailwind CSS v4, React Router v7 |
| Desktop | Tauri v2, Rust, libsql/SQLite, Wouter |
| Backend | FastAPI, SQLAlchemy 2.0, asyncpg, Alembic, Uvicorn |
| ML/Recognition | ONNX Runtime, YOLOv8, OpenCV, pytesseract, EasyOCR |
| Package Mgmt | pnpm workspaces (JS), uv (Python), Cargo (Rust) |
| Build | Docker multi-stage, BuildKit, docker-bake.hcl |
| CI/CD | GitHub Actions, pnpm/uv/Cargo caching, parallel test matrix |
| Observability | OTel, Jaeger, Prometheus, Loki, Grafana |

## Monorepo Structure

```
pokex/
├── apps/
│   ├── web/                    # Vite + React + TypeScript (port 3000)
│   └── desktop-mobile/         # Tauri + React + Rust (port 8000 API)
├── services/
│   ├── data-ingestion/         # FastAPI + PostgreSQL + MinIO (port 8000)
│   ├── recognition/            # FastAPI + YOLOv8 ONNX + EasyOCR (port 8001)
│   └── scraper/                # FastAPI + JustTCG API (port 8002)
├── packages/
│   └── ui/                     # Shared React components (@pokex/ui)
├── test/
│   ├── python/                 # Unit tests (cache, HTTP, Redis)
│   ├── e2e/                    # Integration tests (full cache flow)
│   ├── web/                    # Playwright + Vitest (React Query)
│   └── desktop/                # Rust tests (moka cache, sync)
├── docker-compose.yml          # 12 services
├── docker-bake.hcl             # Parallel Docker builds
└── .github/workflows/ci.yml    # CI: lint, typecheck, build, test
```

## Getting Started

### Prerequisites

- Docker Desktop
- Node.js ≥ 22 (pnpm 9)
- Python ≥ 3.12 (uv)
- Rust (for desktop-mobile)

### Quick Start

```bash
# 1. Start infrastructure
docker compose up -d postgres redis minio

# 2. Build & start all services
docker compose up -d --build data-ingestion scraper recognition web

# 3. Or run Python services locally
cd services/data-ingestion && uv sync --extra dev && uv run uvicorn app.main:app --reload --port 8000
cd services/recognition && uv sync --extra dev && uv run uvicorn app.main:app --reload --port 8001
cd services/scraper && uv sync --extra dev && uv run uvicorn app.main:app --reload --port 8002

# 4. Web app
cd apps/web && pnpm install && pnpm dev
```

### Environment Variables

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
- `test-python` — pytest (48 tests) per service
- `test-web` — Playwright + Vitest
- `test-desktop` — cargo test (12 tests)
- `test-e2e` — full cache flow with Redis

## Links

- [Architecture Overview](architecture/overview.md)
- [Service Specifications](architecture/services.md)
- [Data Flow Diagrams](architecture/data-flows.md)
- [API Reference](api/reference.md)
- [Development Guide](development/local-setup.md)
- [Testing Strategy](development/testing.md)
- [Deployment Guide](deployment/docker.md)
- [CI/CD Pipeline](deployment/ci-cd.md)
- [Contributing Guide](contributing/guidelines.md)