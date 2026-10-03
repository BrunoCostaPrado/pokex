# CI/CD Pipeline

## Overview

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push/PR to `main`.

```
┌─────────────┐
│   Push/PR   │
└──────┬──────┘
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────┐
│   Setup     │────►│    Test      │────►│  Build    │
│  & Cache    │     │  (Matrix)    │     │ & Docker  │
└─────────────┘     └──────────────┘     └───────────┘
      │                   │                   │
      ▼                   ▼                   ▼
- Checkout            - Web (Vitest)         - Docker images
- pnpm/uv/cargo       - Desktop (cargo)      - Push to GHCR
- Cache deps                                    - Multi-platform
- Install Playwright                            (main branch only)
```

---

## Jobs Detail

### 1. Setup & Cache (`setup`)

Runs: `ubuntu-latest`  
Outputs: cache keys for pnpm, uv, cargo

```yaml
steps:
  - Checkout
  - pnpm/action-setup@v4 (v9, no install)
  - setup-node@v4 (Node 22)
  - Cache pnpm store (~/.local/share/pnpm/store + apps/web/node_modules)
  - astral-sh/setup-uv@v4 (uv 0.5.0, cache enabled)
  - Cache uv (~/.cache/uv)
  - Cache cargo (~/.cargo + apps/desktop-mobile/src-tauri/target)
  - pnpm install --frozen-lockfile --prefer-offline --ignore-scripts
  - pnpm --filter web exec playwright install --with-deps chromium
```

Cache keys:
- pnpm: `${{ runner.os }}-pnpm-${{ hashFiles('pnpm-lock.yaml') }}`
- uv: `${{ runner.os }}-uv-${{ hashFiles('services/**/uv.lock') }}`
- cargo: `${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}`

---

### 2. Tests (`test`) — Matrix Strategy

Runs: `ubuntu-latest` (parallel, `fail-fast: false`)  
Needs: `setup`

| Matrix Entry | Target | Steps |
|--------------|--------|-------|
| 1 | `test-web` | pnpm install → playwright install → vitest → build |
| 2 | `test-desktop` | rust-toolchain → cargo test --lib (apps/desktop-mobile/src-tauri) |

Web test command:
```bash
pnpm --filter web run test
pnpm --filter web run build
# Upload apps/web/dist as artifact
```

Desktop test command:
```bash
cd apps/desktop-mobile/src-tauri
cargo test --lib
```

Each matrix entry restores relevant cache from `setup` outputs.

---

### 3. Build & Docker (`build`)

Runs: `ubuntu-latest`  
Needs: `[test]`  
Condition: `github.ref == 'refs/heads/main'` (only on main branch)

```yaml
steps:
  - Checkout
  - docker compose config --quiet (validate)
  - docker/setup-buildx-action@v3
  - docker buildx bake -f docker-bake.hcl
```

Current config builds locally only. For GHCR push, add:
```yaml
  - name: Login to GHCR
    uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GHCR_TOKEN }}

  - name: Build and push
    run: |
      docker buildx bake -f docker-bake.hcl --push
```

---

## Concurrency Control

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

- Cancels in-progress runs for same branch/PR
- Prevents queue buildup on rapid pushes

---

## Environment Variables

```yaml
env:
  NODE_VERSION: 22
  PYTHON_VERSION: "3.12"
  UV_VERSION: "0.5.0"
```

---

## Required Secrets (GitHub Settings → Secrets)

| Secret | Purpose |
|--------|---------|
| `GHCR_TOKEN` | Push Docker images to GHCR (Packages: Write) |
| `JUSTTCG_API_KEY` | Scraper E2E tests (if hitting real API) |

---

## Local CI Simulation (act)

```bash
# Install act
winget install act

# Run specific job
act -j setup
act -j test --matrix target:test-web
act -j test --matrix target:test-desktop
act -j build

# Run full workflow (requires secrets)
act -s GHCR_TOKEN=your_token -s JUSTTCG_API_KEY=your_key

# Run tauri dev locally (from root)
pnpm tauri dev
```

**Known act Limitations:**
- No GitHub-hosted runners (uses local Docker)
- Service containers may not work identically
- Cache actions don't persist between runs
- `GHCR_TOKEN` push fails (expected — no registry auth)
- Artifact upload fails (no ACTIONS_RUNTIME_TOKEN)

---

## Performance Optimizations

| Optimization | Impact |
|--------------|--------|
| pnpm cache (store + node_modules) | ~60s saved on install |
| uv cache (~/.cache/uv) | ~30s saved per Python service |
| cargo cache (registry + target) | ~90s saved on Rust build |
| Playwright cache (~/.cache/ms-playwright) | ~120s saved on browser install |
| Matrix parallelization | 3x Python + Web + Desktop concurrent |
| `fail-fast: false` | All matrix entries run even if one fails |

---

## Adding New Tests

### Python Service Test

1. Add test file in `test/python/test_<feature>.py`
2. Use fixtures from `test/python/conftest.py`
3. Run locally: `uv run pytest test/python/test_<feature>.py -v`
4. CI automatically picks up (pytest discovers all `test_*.py`)

### Web Test

1. Unit: `apps/web/src/**/*.test.tsx`
2. E2E: `apps/web/e2e/<feature>.spec.ts`
3. Run locally: `pnpm test` / `pnpm playwright test`
4. CI runs both in `test-web` matrix

### Desktop Test

1. Add `#[cfg(test)]` module in relevant `.rs` file
2. Or add file in `src/` with `mod tests;`
3. Run locally: `cargo test --lib`
4. CI runs in `test-desktop` matrix

---

## Troubleshooting

### Cache Miss

```bash
# Check cache key in workflow run logs
# Force cache refresh: change pnpm-lock.yaml / uv.lock / Cargo.lock
```

### Flaky Playwright

```yaml
# Add retries in playwright.config.ts
export default defineConfig({
  retries: 2,
  ...
});
```

### uv Sync Fails (Python 3.14)

```bash
# Pin Python 3.12 in workflow
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
```

### Cargo Test Fails (Linking)

```yaml
# Ensure rust-toolchain specifies target
- uses: dtolnay/rust-toolchain@stable
  with:
    target: x86_64-unknown-linux-gnu
```

---

## Workflow Visualization

```
github.event.push/pull_request
         │
         ▼
┌────────────────────────────┐
│       SETUP (1 job)        │
│  Checkout, caches, installs│
└─────────────┬──────────────┘
              │ outputs: cache keys
              ▼
┌────────────────────────────┐
│        TEST (2 parallel)   │
├──────────┬─────────────────┤
│   Web    │    Desktop      │
│ (vitest) │  (cargo test)   │
└────┬─────┴────────┬────────┘
     │              │
     ▼              ▼
┌────────────────────────────┐
│       BUILD (1 job)        │
│    docker buildx bake      │
│   (main branch only)       │
└────────────────────────────┘
```

---

## Migration to Production Deploy

For production deployment, add a `deploy` job:

```yaml
deploy:
  name: Deploy to Production
  runs-on: ubuntu-latest
  needs: build
  if: github.ref == 'refs/heads/main'
  environment: production
  steps:
    - uses: actions/checkout@v4
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/pokex-web \
          web=ghcr.io/your-org/pokex-web:${{ github.sha }}
        kubectl set image deployment/pokex-api \
          api=ghcr.io/your-org/pokex-data-ingestion:${{ github.sha }}
        # ... etc
    - name: Verify deployment
      run: |
        kubectl rollout status deployment/pokex-web
        kubectl rollout status deployment/pokex-api
```