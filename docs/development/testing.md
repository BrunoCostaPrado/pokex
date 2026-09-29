# Testing Strategy

## Test Pyramid

```
                    ┌─────────────┐
                    │   E2E       │  ← Few, high confidence
                    │  (Playwright│     Slow, expensive
                    │   + pytest) │
                   ┌┴─────────────┴┐
                  ┌┴───────────────┴┐
                 ┌┴──── Integration ┴┐  ← Service contracts, cache flows
                ┌┴───────────────────┴┐
               ┌┴──────── Unit ────────┴┐  ← Many, fast, isolated
              ┌┴────────────────────────┴┐
```

## Test Organization

```
test/
├── python/                 # Python unit/integration tests
│   ├── conftest.py         # Shared fixtures (mocks, Redis, DB)
│   ├── test_cache.py       # Cache-Control/ETag middleware
│   ├── test_http.py        # HTTP client behavior
│   ├── test_redis.py       # Redis pub/sub, caching
│   └── test_models.py      # Pydantic/SQLAlchemy models
├── e2e/                    # End-to-end integration tests
│   ├── conftest.py         # Docker compose fixtures
│   ├── test_full_flow.py   # Scraper → DB → API → Cache invalidation
│   └── test_sync.py        # Desktop sync scenarios
├── web/                    # Web app tests
│   ├── components/         # React component tests (Vitest + RTL)
│   ├── hooks/              # Custom hook tests
│   ├── pages/              # Page-level tests
│   └── e2e/                # Playwright tests
│       ├── sets.spec.ts    # Set browsing flow
│       ├── scan.spec.ts    # Camera → recognition flow
│       └── collection.spec.ts
└── desktop/                # Rust tests
    └── src/
        ├── cache_test.rs   # moka TTL cache
        ├── sync_test.rs    # Sync manager
        └── db_test.rs      # SQLite operations
```

## Python Testing (Services)

### Framework Stack

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `pytest-mock` | Mocking |
| `pytest-cov` | Coverage |
| `httpx` | Async HTTP client for API tests |
| `faker` | Test data generation |
| `redis` | Real Redis for integration tests |

### Fixtures (`test/python/conftest.py`)

```python
# Shared across all Python services
@pytest.fixture(scope="session")
def redis_client():
    client = redis.Redis(decode_responses=True)
    yield client
    client.flushdb()

@pytest.fixture
def mock_justtcg_client():
    with patch("services.scraper.app.client.JustTCGClient") as mock:
        yield mock

@pytest.fixture
def sample_set():
    return Set(
        id="sv01",
        name="Scarlet & Violet",
        series="Scarlet & Violet",
        printed_total=198,
        total=198,
        release_date=date(2023, 3, 31),
    )

@pytest.fixture
def sample_card(sample_set):
    return Card(
        id="sv01-1",
        name="Pikachu",
        set_id=sample_set.id,
        number="1/198",
        rarity="Common",
        types=["Lightning"],
        hp=60,
    )
```

### Running Python Tests

```bash
# All services (from repo root)
test-env\Scripts\python.exe -m pytest test/python/ test/e2e/ -v -n 4

# Single service
cd services/data-ingestion
uv run pytest ../../test/python/ -v -n 4

# With coverage
uv run pytest ../../test/python/ --cov=app --cov-report=html

# Specific test
uv run pytest ../../test/python/test_cache.py::test_etag_middleware -v
```

### Python Test Patterns

#### Unit Test (Fast, Isolated)

```python
# test_cache.py
async def test_etag_middleware_returns_304_on_match(
    client: AsyncClient, sample_card: Card
):
    # First request - populate cache
    resp1 = await client.get(f"/api/v1/cards/{sample_card.id}")
    assert resp1.status_code == 200
    etag = resp1.headers["ETag"]
    
    # Second request with If-None-Match
    resp2 = await client.get(
        f"/api/v1/cards/{sample_card.id}",
        headers={"If-None-Match": etag}
    )
    assert resp2.status_code == 304
```

#### Integration Test (Real Dependencies)

```python
# test_redis.py
async def test_cache_invalidation_publishes_to_redis(
    client: AsyncClient, redis_client: redis.Redis, sample_card: Card
):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("cards")
    
    # Trigger write
    await client.patch(f"/api/v1/cards/{sample_card.id}", json={"name": "New"})
    
    # Verify invalidation message
    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
    assert msg["data"] == "INVALIDATE"
```

#### E2E Test (Full Stack)

```python
# test/e2e/test_full_flow.py
@pytest.mark.e2e
async def test_scraper_to_web_invalidation(
    docker_compose: DockerCompose,  # Starts all services
    web_client: AsyncClient,
    redis_client: redis.Redis,
):
    # 1. Run scraper sync
    scraper_client = AsyncClient(base_url="http://scraper:8002")
    await scraper_client.post("/sync/all")
    
    # 2. Wait for data ingestion
    await wait_for(lambda: web_client.get("/api/v1/sets").json()["data"])
    
    # 3. Verify web cache invalidated
    # (React Query would refetch automatically in real app)
    
    # 4. Verify Redis pub/sub
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("cards")
    msg = await pubsub.get_message(timeout=5)
    assert msg["data"] == "INVALIDATE"
```

---

## Web Testing (React + TypeScript)

### Framework Stack

| Tool | Purpose |
|------|---------|
| `vitest` | Unit/test runner |
| `@testing-library/react` | Component testing |
| `@testing-library/jest-dom` | DOM matchers |
| `msw` | API mocking |
| `playwright` | E2E browser tests |

### Unit Tests (Vitest + RTL)

```bash
cd apps/web
pnpm test              # Run all
pnpm test -- --watch   # Watch mode
pnpm coverage          # Coverage report
```

#### Component Test

```tsx
// components/Card.test.tsx
import { render, screen } from "@testing-library/react";
import { Card } from "@pokex/ui";

describe("Card", () => {
  it("renders card with image and rarity badge", () => {
    render(
      <Card
        title="Pikachu"
        subtitle="sv01-1"
        image="/pikachu.webp"
        badge={{ label: "Common", variant: "gray" }}
      />
    );
    
    expect(screen.getByText("Pikachu")).toBeInTheDocument();
    expect(screen.getByText("Common")).toBeInTheDocument();
    expect(screen.getByAltText("Pikachu")).toHaveAttribute("src", "/pikachu.webp");
  });
});
```

#### Hook Test

```tsx
// hooks/useSets.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSets } from "./useSets";
import { server } from "../test/server"; // MSW

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it("fetches sets and caches", async () => {
  const queryClient = new QueryClient();
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  
  const { result } = renderHook(() => useSets(), { wrapper });
  
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toHaveLength(12);
  
  // Second call uses cache
  const { result: result2 } = renderHook(() => useSets(), { wrapper });
  expect(result2.current.data).toBe(result.current.data); // Same reference
});
```

#### MSW Handlers (`test/handlers.ts`)

```typescript
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("http://localhost:8000/api/v1/sets", () => {
    return HttpResponse.json({
      data: [{ id: "sv01", name: "Scarlet & Violet", ... }],
      pagination: { page: 1, limit: 50, total: 12, totalPages: 1 },
    });
  }),
  
  http.post("http://localhost:8001/recognize", async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get("file");
    return HttpResponse.json({
      detections: [{ bbox: [0,0,1,1], confidence: 0.9, class_id: 0, class_name: "card" }],
      ocr_results: [{ text: "Pikachu", confidence: 0.9, bbox: [0,0,1,1] }],
      processing_time_ms: 100,
    });
  }),
];
```

### E2E Tests (Playwright)

```bash
cd apps/web
pnpm playwright install --with-deps chromium
pnpm playwright test              # Headless
pnpm playwright test --ui         # UI mode
pnpm playwright test --headed     # Visible browser
pnpm playwright show-report       # HTML report
```

#### Page Object Pattern

```typescript
// e2e/pages/SetsPage.ts
import { Page, Locator, expect } from "@playwright/test";

export class SetsPage {
  readonly page: Page;
  readonly setGrid: Locator;
  readonly searchInput: Locator;
  readonly loadMoreButton: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.setGrid = page.locator('[data-testid="set-grid"]');
    this.searchInput = page.locator('[data-testid="search-input"]');
    this.loadMoreButton = page.locator('[data-testid="load-more"]');
  }
  
  async goto() {
    await this.page.goto("/sets");
    await this.page.waitForLoadState("networkidle");
  }
  
  async search(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForLoadState("networkidle");
  }
  
  async expectSetCount(count: number) {
    await expect(this.setGrid.locator('[data-testid="set-card"]')).toHaveCount(count);
  }
  
  async clickSet(id: string) {
    await this.page.locator(`[data-testid="set-card-${id}"]`).click();
    await this.page.waitForURL(`**/sets/${id}`);
  }
}
```

#### E2E Test

```typescript
// e2e/sets.spec.ts
import { test, expect } from "@playwright/test";
import { SetsPage } from "./pages/SetsPage";

test.describe("Sets browsing", () => {
  let setsPage: SetsPage;
  
  test.beforeEach(async ({ page }) => {
    setsPage = new SetsPage(page);
    await setsPage.goto();
  });
  
  test("displays set grid with 12 sets", async () => {
    await setsPage.expectSetCount(12);
  });
  
  test("filters sets by search", async () => {
    await setsPage.search("Scarlet");
    await setsPage.expectSetCount(3); // sv01, sv02, sv03
  });
  
  test("navigates to set detail", async () => {
    await setsPage.clickSet("sv01");
    await expect(page.locator('[data-testid="set-detail"]')).toBeVisible();
    await expect(page.locator('[data-testid="set-name"]')).toContainText("Scarlet & Violet");
  });
});
```

---

## Desktop Testing (Rust)

### Framework Stack

| Tool | Purpose |
|------|---------|
| `cargo test` | Built-in test runner |
| `moka` | Cache testing |
| `sqlx` / `libsql` | Database testing |
| `mockito` | HTTP mocking (optional) |

### Running Tests

```bash
cd apps/desktop-mobile/src-tauri

# All tests
cargo test

# Library tests only (no integration)
cargo test --lib

# Specific test
cargo test cache::tests::test_ttl_expiration

# With output
cargo test -- --nocapture
```

### Cache Tests

```rust
// src/cache_test.rs
use moka::future::Cache;
use std::time::Duration;

#[tokio::test]
async fn test_ttl_expiration() {
    let cache: Cache<String, String> = Cache::builder()
        .time_to_live(Duration::from_millis(100))
        .build();
    
    cache.insert("key".to_string(), "value".to_string()).await;
    assert_eq!(cache.get("key").await, Some("value".to_string()));
    
    tokio::time::sleep(Duration::from_millis(150)).await;
    assert_eq!(cache.get("key").await, None);
}

#[tokio::test]
async fn test_cache_invalidation() {
    let cache: Cache<String, Vec<Card>> = Cache::builder()
        .max_capacity(100)
        .build();
    
    cache.insert("cards".to_string(), vec![card1, card2]).await;
    assert_eq!(cache.get("cards").await.unwrap().len(), 2);
    
    cache.invalidate("cards").await;
    assert_eq!(cache.get("cards").await, None);
}
```

### Sync Tests

```rust
// src/sync_test.rs
#[tokio::test]
async fn test_full_sync_replaces_local_data() {
    let db = setup_test_db().await;
    let sync_mgr = SyncManager::new(db.clone(), mock_api_client());
    
    // Pre-populate with old data
    insert_sets(&db, vec![old_set()]).await;
    
    // Run full sync
    let result = sync_mgr.full_sync().await.unwrap();
    
    // Verify replaced
    let sets = get_all_sets(&db).await;
    assert_eq!(sets.len(), 12); // From mock API
    assert!(result.sets_synced > 0);
}
```

---

## CI Test Execution

### GitHub Actions Matrix

```yaml
# .github/workflows/ci.yml
test:
  strategy:
    matrix:
      include:
        - target: test-python
          service: data-ingestion
          workers: "4"
        - target: test-python
          service: recognition
          workers: "2"
        - target: test-python
          service: scraper
          workers: "4"
        - target: test-web
        - target: test-desktop
```

### Test Commands

```bash
# Python (per service)
cd services/${{ matrix.service }}
uv run pytest test/ -v --tb=short -n ${{ matrix.workers }}

# Web
pnpm --filter web run test
pnpm --filter web run build

# Desktop
cd apps/desktop-mobile/src-tauri
cargo test --lib
```

### Coverage Requirements

| Layer | Target | Enforced |
|-------|--------|----------|
| Python unit | ≥ 80% | CI fails if below |
| Web unit | ≥ 70% | Report only |
| Rust unit | ≥ 60% | Report only |
| E2E | Critical paths | Manual review |

---

## Test Data Management

### Factories (Python)

```python
# test/factories.py
from faker import Faker
from app.models import Set, Card, Price

fake = Faker()

def create_set(**overrides) -> Set:
    defaults = {
        "id": fake.bothify("sv##"),
        "name": fake.catch_phrase(),
        "series": "Scarlet & Violet",
        "printed_total": fake.random_int(150, 250),
        "total": fake.random_int(150, 250),
        "release_date": fake.date_between(start_date="-2y", end_date="today"),
    }
    defaults.update(overrides)
    return Set(**defaults)

def create_card(set_id: str, **overrides) -> Card:
    defaults = {
        "id": f"{set_id}-{fake.random_int(1, 200)}",
        "name": fake.name(),
        "set_id": set_id,
        "number": f"{fake.random_int(1, 200)}/200",
        "rarity": fake.random_element(["Common", "Uncommon", "Rare", "Double Rare"]),
        "types": [fake.random_element(["Fire", "Water", "Grass", "Lightning", "Psychic", "Fighting", "Darkness", "Metal", "Fairy", "Dragon", "Colorless"])],
        "hp": fake.random_int(30, 350),
    }
    defaults.update(overrides)
    return Card(**defaults)
```

### Database Seeding (E2E)

```python
# test/e2e/conftest.py
@pytest.fixture(scope="session")
async def seeded_db(docker_compose):
    # Run scraper to populate real data
    async with AsyncClient(base_url="http://scraper:8002") as client:
        await client.post("/sync/all")
    
    # Verify data exists
    async with AsyncClient(base_url="http://data-ingestion:8000") as client:
        resp = await client.get("/api/v1/sets")
        assert len(resp.json()["data"]) > 0
    
    yield
```

---

## Performance Testing (Future)

### Load Test Targets

| Endpoint | Target RPS | P99 Latency |
|----------|------------|-------------|
| `GET /api/v1/sets` | 100 | < 200ms |
| `GET /api/v1/cards` | 200 | < 150ms |
| `POST /recognize` | 10 | < 2s (CPU) / < 500ms (GPU) |

### Tooling

- `k6` for load testing
- `locust` for Python service benchmarks
- Run in staging environment only

---

## Flaky Test Protocol

1. **Quarantine**: Move to `test/flaky/` with `@pytest.mark.flaky`
2. **Investigate**: Root cause within 48h
3. **Fix or Delete**: No flaky tests in main branch
4. **Track**: GitHub issue with `flaky-test` label