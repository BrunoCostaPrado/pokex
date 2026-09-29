# Coding Standards

## General Principles

1. Consistency over preference — Follow existing patterns in the codebase
2. Explicit over implicit — Type annotations, clear names, no magic
3. Boring over clever — Standard library first, minimal dependencies
4. Test behavior, not implementation — Public API contracts
5. Fail fast — Validate at boundaries, crash early with clear messages

---

## TypeScript / JavaScript (Web, Desktop, UI)

### Formatting & Linting

Tool: Biome (configured in root `biome.json`)

```bash
# Check + fix
pnpm biome check --write .

# Format only
pnpm biome format --write .
```

Rules: 2-space indent, single quotes, trailing commas, 100 char line length

### Type Safety

```typescript
// Explicit types for public APIs
export interface Set {
  id: string;
  name: string;
  series: string;
  printedTotal: number;
  total: number;
  releaseDate: string; // ISO 8601
  images: { symbol: string; logo: string };
}

// Generic constraints
function fetchPaginated<T>(url: string): Promise<PaginatedResponse<T>>;

// Avoid any
function process(data: any) { ... }

// Use unknown for external data
function parseJson(json: unknown): Result<Set, Error> { ... }
```

### React Patterns

```tsx
// Functional components with explicit props
interface CardProps {
  title: string;
  subtitle?: string;
  image?: string;
  badge?: BadgeProps;
  onClick?: () => void;
}

export function Card({ title, subtitle, image, badge, onClick }: CardProps) {
  return (
    <article className="card" onClick={onClick}>
      {image && <img src={image} alt={title} />}
      <h3>{title}</h3>
      {subtitle && <span>{subtitle}</span>}
      {badge && <Badge {...badge} />}
    </article>
  );
}

// Custom hooks for data fetching
function useSets() {
  return useQuery({
    queryKey: ["sets"],
    queryFn: () => api.getSets(),
    staleTime: 60_000,
    gcTime: 300_000,
  });
}

// Don't put logic in components
// Extract to hooks/utils
```

### State Management

| Scope | Solution |
|-------|----------|
| Server data | TanStack Query (React Query) |
| Client UI state | React Context + useReducer |
| Form state | React Hook Form + Zod |
| Persisted | localStorage / IndexedDB (explicit keys) |

### API Client

```typescript
// lib/api.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 10_000,
});

// Request interceptor for auth (future)
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor for errors
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      // Handle auth expiry
    }
    return Promise.reject(error);
  }
);

export const setsApi = {
  list: (params?: ListParams) => api.get("/api/v1/sets", { params }),
  get: (id: string) => api.get(`/api/v1/sets/${id}`),
  create: (data: CreateSetDto) => api.post("/api/v1/sets", data),
};
```

### Imports Order

```typescript
// 1. External packages
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

// 2. Internal packages (workspace)
import { Button, Card } from "@pokex/ui";

// 3. Relative imports
import { useSets } from "./hooks/useSets";
import { Set } from "./types";
import "./styles.css";
```

---

## Python (Services)

### Formatting & Linting

Tools: Ruff (lint + format), mypy (type check)

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

Config (`pyproject.toml`):
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
select = ["E", "F", "I", "UP", "W"]
ignore = ["E501", "UP007"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
disallow_untyped_defs = true
ignore_missing_imports = true
```

### Type Annotations

```python
# Full annotations on public functions
async def get_sets(
    page: int = 1,
    limit: int = 50,
    series: str | None = None,
) -> PaginatedResponse[Set]:
    ...

# Type aliases for complex types
type CardFilters = dict[str, str | int | None]
type PriceSource = Literal["tcgplayer", "ebay", "cardmarket"]

# Pydantic models for validation
class SetCreate(BaseModel):
    id: str = Field(pattern=r"^sv\d{2}$")
    name: str = Field(min_length=1, max_length=255)
    series: str
    printed_total: int = Field(ge=0)
    total: int = Field(ge=0)
    release_date: date
    images: SetImages

# Avoid untyped dicts for structured data
# def create_set(data: dict) -> Set:  # Bad
```

### FastAPI Patterns

```python
# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Data Ingestion API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# Router with prefix
router = APIRouter(prefix="/api/v1", tags=["sets"])

@router.get("/sets", response_model=PaginatedResponse[Set])
async def list_sets(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    series: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    ...
```

### Error Handling

```python
# exceptions.py
class PokexError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code

class NotFoundError(PokexError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} not found: {id}", "NOT_FOUND", 404)

class ValidationError(PokexError):
    def __init__(self, errors: list[dict]):
        super().__init__("Validation failed", "VALIDATION_ERROR", 422)
        self.errors = errors

# Global handler
@app.exception_handler(PokexError)
async def pokex_error_handler(request: Request, exc: PokexError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )
```

### Async Patterns

```python
# Use async for I/O
async def fetch_cards(set_id: str) -> list[Card]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{JUSTTCG_URL}/cards/{set_id}")
        resp.raise_for_status()
        return [Card(**c) for c in resp.json()]

# Concurrent with gather
async def sync_all_sets(set_ids: list[str]) -> list[Card]:
    tasks = [fetch_cards(sid) for sid in set_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]

# Semaphore for rate limiting
semaphore = asyncio.Semaphore(5)

async def rate_limited_fetch(url: str) -> dict:
    async with semaphore:
        return await fetch_with_retry(url)
```

### Database Patterns

```python
# repositories/sets.py
class SetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, id: str) -> Set | None:
        stmt = select(SetModel).where(SetModel.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_paginated(
        self, 
        page: int, 
        limit: int, 
        filters: SetFilters
    ) -> PaginatedResponse[Set]:
        stmt = select(SetModel)
        # Apply filters...
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return PaginatedResponse(
            data=[Set.model_validate(m) for m in items],
            page=page, limit=limit, total=total, total_pages=(total + limit - 1) // limit
        )
    
    async def upsert(self, set_data: SetCreate) -> Set:
        stmt = (
            insert(SetModel)
            .values(**set_data.model_dump())
            .on_conflict_do_update(
                index_elements=["id"],
                set_=set_data.model_dump(exclude={"id"})
            )
            .returning(SetModel)
        )
        result = await self.session.execute(stmt)
        return Set.model_validate(result.scalar_one())
```

---

## Rust (Desktop Backend)

### Formatting & Linting

```bash
cargo fmt --check
cargo clippy -- -D warnings
```

### Patterns

```rust
// Use Result for fallible operations
pub async fn get_sets(&self) -> Result<Vec<Set>, AppError> {
    let mut conn = self.db.acquire().await?;
    let sets = sqlx::query_as!(Set, "SELECT * FROM sets")
        .fetch_all(&mut *conn)
        .await?;
    Ok(sets)
}

// Builder pattern for complex types
pub struct SyncConfig {
    pub batch_size: usize,
    pub timeout: Duration,
    pub retry_attempts: u32,
}

impl Default for SyncConfig {
    fn default() -> Self {
        Self {
            batch_size: 100,
            timeout: Duration::from_secs(30),
            retry_attempts: 3,
        }
    }
}

// Tauri commands with proper error handling
#[tauri::command]
pub async fn sync_full(state: State<'_, AppState>) -> Result<SyncResult, String> {
    state.sync_manager.full_sync().await
        .map_err(|e| format!("Sync failed: {}", e))
}
```

---

## Git Conventions

### Commit Messages (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without behavior change |
| `perf` | Performance improvement |
| `docs` | Documentation only |
| `test` | Adding tests |
| `chore` | Maintenance (deps, config, CI) |
| `build` | Build system changes |

Examples:
```
feat(web): add card scan page with camera integration

fix(data-ingestion): handle duplicate card upsert correctly

refactor(ui): extract Button variant logic to separate hook

perf(recognition): batch ONNX inference for multiple crops

chore(deps): update pydantic to 2.9.2
```

### Branch Naming

```
<type>/<short-description>
feat/card-scan-page
fix/recognition-timeout
refactor/cache-invalidation
```

### PR Requirements

- [ ] All CI checks pass
- [ ] Tests added/updated for new behavior
- [ ] Documentation updated if public API changed
- [ ] No merge commits (rebase onto main)
- [ ] Single commit per logical change (squash if needed)

---

## Dependency Management

### JavaScript

```bash
# Add dependency
pnpm add <package> --filter web

# Add dev dependency
pnpm add -D <package> --filter web

# Update
pnpm update --latest --filter web
```

### Python

```bash
# Add to pyproject.toml manually, then:
uv sync --extra dev

# Or use uv add
uv add <package> --dev
```

### Rust

```bash
cd apps/desktop-mobile/src-tauri
cargo add <crate>
cargo update
```

---

## Security

- Never commit secrets — Use `.env` (gitignored) or GitHub Secrets
- Validate all inputs — Pydantic/Zod at boundaries
- Parameterized queries — SQLAlchemy ORM / sqlx macros
- HTTPS in production — TLS termination at load balancer
- CORS — Explicit origins, no wildcards in prod
- Rate limiting — Implement per-endpoint (TODO)