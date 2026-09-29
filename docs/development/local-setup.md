# Local Development Setup

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | Latest | https://docker.com |
| Node.js | ≥ 22 | `winget install OpenJS.NodeJS` or nvm |
| pnpm | 9 | `corepack enable && corepack prepare pnpm@9 --activate` |
| Python | ≥ 3.12 | `winget install Python.Python.3.12` |
| uv | Latest | `pip install uv` or `pipx install uv` |
| Rust | Stable | `winget install Rustlang.Rust` |

**Windows Notes:**
- Use PowerShell 7+ (`pwsh`)
- Enable long paths: `git config --system core.longpaths true`
- WSL2 recommended for Docker performance

---

## Repository Setup

```bash
# Clone
git clone https://github.com/your-org/pokex.git
cd pokex

# Install JS dependencies (root + workspaces)
pnpm install

# Verify Python services
cd services/data-ingestion && uv sync --extra dev
cd ../recognition && uv sync --extra dev
cd ../scraper && uv sync --extra dev

# Verify Rust (desktop)
cd apps/desktop-mobile/src-tauri && cargo check
```

---

## Environment Configuration

### Root `.env`

```bash
# Copy example
cp .env.example .env

# Required values
JUSTTCG_API_KEY=your_justtcg_key_here
DATABASE_URL=postgresql+asyncpg://pokeuser:pokepass@localhost:5432/pokedb
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=pokemon-cards

# Optional service URLs (for web/desktop)
NEXT_PUBLIC_RECOGNITION_URL=http://localhost:8001
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_RECOGNITION_URL=http://localhost:8001
```

### Service-Specific `.env` (Optional)

Each service can have its own `.env` in its directory for overrides:

```
services/data-ingestion/.env
services/recognition/.env
services/scraper/.env
```

---

## Running Services

### Option 1: Docker Compose (Recommended)

```bash
# Start infrastructure only
docker compose up -d postgres redis minio

# Start all services
docker compose up -d --build data-ingestion scraper recognition web

# View logs
docker compose logs -f data-ingestion

# Stop
docker compose down
```

**Ports:**
| Service | Port | URL |
|---------|------|-----|
| PostgreSQL | 5432 | `postgresql://pokeuser:pokepass@localhost:5432/pokedb` |
| Redis | 6379 | `redis://localhost:6379` |
| MinIO API | 9000 | `http://localhost:9000` |
| MinIO Console | 9001 | `http://localhost:9001` (minioadmin/minioadmin) |
| Data Ingestion | 8000 | `http://localhost:8000/docs` |
| Recognition | 8001 | `http://localhost:8001/docs` |
| Scraper | 8002 | `http://localhost:8002/docs` |
| Web | 3000 | `http://localhost:3000` |

### Option 2: Local Python Services + Docker Infra

```bash
# Terminal 1: Infrastructure
docker compose up -d postgres redis minio

# Terminal 2: Data Ingestion
cd services/data-ingestion
uv run uvicorn app.main:app --reload --port 8000

# Terminal 3: Recognition
cd services/recognition
uv run uvicorn app.main:app --reload --port 8001

# Terminal 4: Scraper
cd services/scraper
uv run uvicorn app.main:app --reload --port 8002

# Terminal 5: Web
cd apps/web
pnpm dev
```

### Option 3: Fully Local (No Docker)

Requires local PostgreSQL, Redis, MinIO instances.

```bash
# Start PostgreSQL, Redis, MinIO locally
# Update .env with local connection strings

# Then same as Option 2
```

---

## Running Desktop App

```bash
cd apps/desktop-mobile

# Install deps
pnpm install

# Development (with hot reload)
pnpm tauri dev

# Build
pnpm tauri build
```

**Note:** First build downloads Rust toolchain and compiles native code (~5-10 min).

---

## Database Migrations

```bash
# Data Ingestion only (uses Alembic)
cd services/data-ingestion

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1

# Show history
uv run alembic history
```

---

## Code Quality Commands

### JavaScript/TypeScript (Web, Desktop, UI)

```bash
# From repo root
pnpm lint              # biome check --write (all workspaces)
pnpm typecheck         # tsc --noEmit (all workspaces)
pnpm test              # vitest run (web)

# Per workspace
cd apps/web && pnpm lint
cd apps/web && pnpm typecheck
cd apps/web && pnpm test
cd apps/web && pnpm build

cd packages/ui && pnpm lint
cd packages/ui && pnpm typecheck
cd packages/ui && pnpm build
```

### Python (Services)

```bash
# Per service
cd services/data-ingestion
uv run ruff check .
uv run ruff format .
uv run mypy .

# Tests
uv run pytest test/ -v --tb=short -n 4
uv run pytest test/ --cov=app --cov-report=term-missing
```

### Rust (Desktop)

```bash
cd apps/desktop-mobile/src-tauri
cargo check
cargo clippy
cargo fmt --check
cargo test --lib
```

---

## Testing

### Python Unit/Integration Tests

```bash
# All Python tests
cd D:\github\pokex
test-env\Scripts\python.exe -m pytest test/python/ test/e2e/ -v

# Per service
cd services/data-ingestion && uv run pytest ../../test/python/ -v -k "data_ingestion"
cd services/recognition && uv run pytest ../../test/python/ -v -k "recognition"
cd services/scraper && uv run pytest ../../test/python/ -v -k "scraper"

# E2E (requires Redis)
docker compose up -d redis
cd D:\github\pokex
test-env\Scripts\python.exe -m pytest test/e2e/ -v -n 4
```

### Web Tests

```bash
cd apps/web

# Unit tests (Vitest)
pnpm test

# E2E tests (Playwright)
pnpm playwright install --with-deps chromium
pnpm playwright test

# Coverage
pnpm coverage
```

### Desktop Tests

```bash
cd apps/desktop-mobile/src-tauri
cargo test --lib
```

---

## Debugging

### VS Code Launch Configurations

```json
// .vscode/launch.json
{
  "configurations": [
    {
      "name": "Python: Data Ingestion",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/services/data-ingestion",
      "envFile": "${workspaceFolder}/services/data-ingestion/.env"
    },
    {
      "name": "Python: Recognition",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8001"],
      "cwd": "${workspaceFolder}/services/recognition",
      "envFile": "${workspaceFolder}/services/recognition/.env"
    },
    {
      "name": "Attach to Web (Chrome)",
      "type": "chrome",
      "request": "attach",
      "port": 9222,
      "urlFilter": "http://localhost:3000/*",
      "webRoot": "${workspaceFolder}/apps/web/src"
    }
  ]
}
```

### Python Debugging Tips

```python
# Add breakpoint
import breakpoint; breakpoint()

# Or use debugger
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

### React Query Devtools

```tsx
// In development, React Query Devtools auto-included
// Open browser devtools → "React Query" tab
```

---

## Common Issues

### pnpm Install Fails

```bash
# Clear cache and retry
pnpm store prune
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### uv Sync Fails (Python 3.14)

```bash
# pydantic-core not yet compatible with 3.14
# Use Python 3.12 for now
uv python install 3.12
uv python pin 3.12
uv sync --extra dev
```

### Docker Build Fails (Web)

```bash
# Ensure packages/ui is copied before pnpm install
# Check apps/web/Dockerfile COPY order
```

### Port Conflicts

```bash
# Find process on port
netstat -ano | findstr :8000
# Kill
taskkill /PID <pid> /F
```

### MinIO Bucket Not Created

```bash
# Auto-create on first service start
# Or manually:
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/pokemon-cards
mc anonymous set public local/pokemon-cards
```

---

## IDE Recommendations

### VS Code Extensions

| Extension | Purpose |
|-----------|---------|
| Biome | Lint/format JS/TS |
| Ruff | Lint/format Python |
| Rust Analyzer | Rust support |
| Tauri | Tauri integration |
| Tailwind CSS IntelliSense | Tailwind v4 |
| Error Lens | Inline errors |
| GitLens | Git history |

### Settings (`.vscode/settings.json`)

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[typescript]": {
    "editor.defaultFormatter": "biomejs.biome"
  },
  "[rust]": {
    "editor.defaultFormatter": "rust-lang.rust-analyzer"
  }
}
```