# Service Specifications

## Data Ingestion Service

**Port**: 8000  
**Stack**: FastAPI 0.115, SQLAlchemy 2.0, asyncpg, Alembic, Uvicorn  
**Workers**: 4 (gunicorn + UvicornWorker)  
**Health**: `GET /health`

### Responsibilities

- CRUD operations for Pokémon TCG sets, cards, prices
- Image upload to MinIO with metadata persistence
- Cache-Control/ETag middleware for HTTP caching
- Redis-backed cache invalidation via Pub/Sub

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/sets` | List all sets (paginated) |
| GET | `/api/v1/sets/{id}` | Get set by ID |
| POST | `/api/v1/sets` | Create set |
| PATCH | `/api/v1/sets/{id}` | Update set |
| DELETE | `/api/v1/sets/{id}` | Delete set |
| GET | `/api/v1/cards` | List cards (filterable) |
| GET | `/api/v1/cards/{id}` | Get card by ID |
| POST | `/api/v1/cards` | Create card |
| GET | `/api/v1/cards/{id}/image` | Get card image (redirects to MinIO) |
| POST | `/api/v1/cards/{id}/image` | Upload card image |
| GET | `/api/v1/prices` | List prices (filterable) |
| GET | `/api/v1/prices/{card_id}` | Get prices for card |

### Database Schema

```sql
-- sets
CREATE TABLE sets (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    series VARCHAR(255),
    printed_total INTEGER,
    total INTEGER,
    release_date DATE,
    symbol_url TEXT,
    logo_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- cards
CREATE TABLE cards (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    set_id VARCHAR(50) REFERENCES sets(id),
    number VARCHAR(20),
    rarity VARCHAR(50),
    small_image_url TEXT,
    large_image_url TEXT,
    types TEXT[],
    hp INTEGER,
    artist VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- prices
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    card_id VARCHAR(50) REFERENCES cards(id),
    source VARCHAR(50) NOT NULL,
    price INTEGER NOT NULL,  -- USD cents
    currency VARCHAR(3) DEFAULT 'USD',
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(card_id, source)
);

-- images (MinIO metadata)
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id VARCHAR(50) REFERENCES cards(id),
    object_key VARCHAR(500) NOT NULL,
    content_type VARCHAR(100),
    size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Caching Strategy

```python
# Middleware (data_ingestion_app/main.py)
@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    # GET requests: check ETag/If-None-Match
    # Set Cache-Control: public, max-age=300, stale-while-revalidate=60
    # On write: publish INVALIDATE to Redis channel
```

### Configuration

```python
# config.py (pydantic-settings)
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_bucket: str = "pokemon-cards"
    image_storage_path: str = "/app/images"
    
    class Config:
        env_file = ".env"
```

---

## Recognition Service

**Port**: 8001  
**Stack**: FastAPI, ONNX Runtime, OpenCV, pytesseract, EasyOCR  
**Workers**: 2 (gunicorn + UvicornWorker)  
**Health**: `GET /health`

### Responsibilities

- Card detection via YOLOv8 ONNX model
- Text extraction via OCR (EasyOCR primary, pytesseract fallback)
- Return bounding boxes, confidence scores, extracted text

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/recognize` | Detect cards in uploaded image |
| POST | `/recognize/batch` | Batch recognition (max 10 images) |

### Request/Response

```typescript
// POST /recognize
// Request: multipart/form-data with "file" (image)
interface RecognizeResponse {
  detections: DetectionResult[];
  ocr_results: OCRResult[];
  processing_time_ms: number;
}

interface DetectionResult {
  bbox: [number, number, number, number];  // x, y, w, h (normalized 0-1)
  confidence: number;
  class_id: number;
  class_name: "card" | "energy" | "trainer";
}

interface OCRResult {
  text: string;
  confidence: number;
  bbox: [number, number, number, number];
}
```

### Model Details

- **YOLOv8n ONNX**: ~6MB, 320x320 input, 80 classes (COCO) + custom card classes
- **Input**: Preprocessed to 320x320, normalized [0,1], RGB
- **Output**: [1, 84, 8400] → NMS (IoU 0.45, conf 0.25)
- **Classes**: `0=card`, `1=energy`, `2=trainer` (custom trained)

### Performance

| Metric | Value |
|--------|-------|
| Latency (CPU) | ~150ms/image |
| Latency (GPU) | ~30ms/image |
| Throughput (CPU) | ~6 img/s |
| Memory | ~500MB base + 100MB/model |

### Configuration

```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_bucket: str = "pokemon-cards"
    model_path: str = "/app/models/yolov8n_card.onnx"
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
```

---

## Scraper Service

**Port**: 8002  
**Stack**: FastAPI, httpx, pydantic-settings  
**Workers**: 4 (gunicorn + UvicornWorker)  
**Health**: `GET /health`

### Responsibilities

- Pull sets, cards, prices from JustTCG API
- Transform and upsert into PostgreSQL via Data Ingestion API
- Handle rate limiting, pagination, retries
- Incremental sync support (since timestamp)

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/sync/sets` | Full set sync |
| POST | `/sync/cards` | Full card sync (requires sets) |
| POST | `/sync/prices` | Price sync |
| POST | `/sync/all` | Full pipeline (sets → cards → prices) |
| POST | `/sync/incremental` | Incremental since timestamp |

### JustTCG Integration

```python
# Base URL: https://api.justtcg.com/v1
# Auth: Bearer token (JUSTTCG_API_KEY)
# Rate limit: 60 req/min (enforced by API)

class JustTCGClient:
    async def get_sets(self) -> list[Set]:
        ...
    async def get_cards(self, set_id: str) -> list[Card]:
        ...
    async def get_prices(self, card_id: str) -> list[Price]:
        ...
```

### Sync Logic

```
1. GET /sets → upsert sets via Data Ingestion POST /api/v1/sets
2. For each set: GET /cards/{set_id} → upsert cards
3. For each card: GET /prices/{card_id} → upsert prices
4. On completion: PUBLISH "cards" INVALIDATE to Redis
```

### Configuration

```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_bucket: str = "pokemon-cards"
    data_api_url: str = "http://data-ingestion:8000"
    justtcg_api_key: str
    justtcg_base_url: str = "https://api.justtcg.com/v1"
    sync_batch_size: int = 100
    request_timeout: float = 30.0
    max_retries: int = 3
```

---

## Web Application

**Port**: 3000 (dev), 80/443 (prod via nginx)  
**Stack**: React 19, TypeScript, Vite 5, TanStack Query v5, Tailwind CSS v4, React Router v7  
**Build**: `pnpm build` → static files in `dist/`

### Features

| Route | Description |
|-------|-------------|
| `/` | Dashboard (recent sets, collection stats) |
| `/sets` | Browse all sets (infinite scroll, search) |
| `/sets/:id` | Set detail with card grid |
| `/scan` | Camera upload → Recognition service |
| `/collection` | User collection (localStorage + sync) |
| `/settings` | API URLs, theme, sync options |

### State Management

- **Server State**: TanStack Query (caching, invalidation, optimistic updates)
- **Client State**: React Context (theme, user preferences)
- **Persistence**: localStorage (collection), IndexedDB (offline queue)

### Shared UI Package

`@pokex/ui` provides 9 components used by both web and desktop-mobile:

| Component | Description |
|-----------|-------------|
| `CardCard` | Card display with image, set info, rarity |
| `CardDetail` | Full card view with prices, images |
| `Collection` | Grid of collected cards |
| `Scan` | Camera scan UI |
| `SetDetail` | Set overview with cards |
| `SetsList` | Paginated set list |
| `LoadingState`/`ErrorState`/`EmptyState` | Shared states |
| `ThemeToggle` | Dark/light mode switch |
| `Separator` | Visual divider |

### Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@pokex/ui': path.resolve(__dirname, '../../packages/ui/src'),
    },
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
});
```

---

## Desktop-Mobile Application

**Stack**: Tauri v2, React 19, TypeScript, Vite 5, Rust (libsql/SQLite), Wouter (router)  
**Build**: `pnpm tauri build` → native binaries

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Tauri App                          │
├─────────────────────┬───────────────────────────────┤
│    Frontend         │         Backend (Rust)        │
│  (React + Vite)     │  (Tauri commands + SQLite)    │
├─────────────────────┼───────────────────────────────┤
│ • Sets, Cards UI    │ • SQLite database (libsql)    │
│ • Scan (camera)     │ • Full/Incremental sync       │
│ • Collection        │ • moka TTL cache (API URLs)   │
│ • Offline queue     │ • Native dialogs, FS access   │
│ • Wouter router     │ • System tray, notifications  │
└─────────────────────┴───────────────────────────────┘
```

### Rust Commands (Tauri)

```rust
// src-tauri/src/commands.rs
#[tauri::command]
async fn get_sets() -> Result<Vec<Set>, String> { ... }

#[tauri::command]
async fn get_cards(set_id: String) -> Result<Vec<Card>, String> { ... }

#[tauri::command]
async fn sync_full() -> Result<SyncResult, String> { ... }

#[tauri::command]
async fn sync_incremental(since: DateTime<Utc>) -> Result<SyncResult, String> { ... }

#[tauri::command]
async fn recognize_image(base64: String) -> Result<RecognitionResult, String> { ... }
```

### SQLite Schema (libsql)

```sql
-- Local mirror of server data
CREATE TABLE sets (...);      -- Same as server
CREATE TABLE cards (...);     -- Same as server
CREATE TABLE prices (...);    -- Same as server

-- Sync metadata
CREATE TABLE sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at INTEGER NOT NULL  -- Unix timestamp
);

-- Offline mutation queue
CREATE TABLE pending_mutations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,         -- 'create' | 'update' | 'delete'
    entity TEXT NOT NULL,       -- 'set' | 'card' | 'collection_item'
    payload TEXT NOT NULL,      -- JSON
    created_at INTEGER NOT NULL,
    retry_count INTEGER DEFAULT 0
);
```

### Sync Strategy

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Full** | Manual / First run | Download all sets → cards → prices; replace local |
| **Incremental** | Periodic / App focus | Download changes since `last_sync`; merge |
| **Background** | Periodic timer | Incremental every 30 min when online |

### Configuration

```toml
# src-tauri/tauri.conf.json
{
  "identifier": "com.pokex.app",
  "build": { "frontendDist": "../dist" },
  "plugins": {
    "sql": { "preload": ["sqlite:pokex.db"] },
    "fs": { "scope": ["$APPDATA/pokex/*"] }
  }
}
```

---

## Shared UI Package (@pokex/ui)

**Location**: `packages/ui/`  
**Exports**: `src/index.ts` (all components + types)  
**Peer Dependencies**: React 19, React DOM, TanStack Query, React Router

### Component API

```typescript
// Button
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

// Card
interface CardProps {
  title: string;
  subtitle?: string;
  image?: string;
  badge?: BadgeProps;
  children?: React.ReactNode;
  onClick?: () => void;
}

// Modal
interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'full';
}

// Toast
interface ToastProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;  // default 5000ms
}
```

### Usage

```typescript
// In web or desktop-mobile
import { Button, Card, Modal, Toast } from '@pokex/ui';
import '@pokex/ui/styles.css';  // Tailwind v4 import
```

---

## Infrastructure Services

### PostgreSQL

| Setting | Value |
|---------|-------|
| Image | `postgres:16-alpine` |
| Port | 5432 |
| User | `pokeuser` |
| Database | `pokedb` |
| Extensions | `uuid-ossp`, `pg_trgm` |

### Redis

| Setting | Value |
|---------|-------|
| Image | `redis:7-alpine` |
| Port | 6379 |
| Persistence | AOF (`appendonly yes`) |
| Max Memory | 256MB (policy: allkeys-lru) |

### MinIO

| Setting | Value |
|---------|-------|
| Image | `elestio/minio:latest` |
| API Port | 9000 |
| Console Port | 9001 |
| Root User | `minioadmin` |
| Bucket | `pokemon-cards` |
| Policy | Public read for card images |

### Observability

| Component | Image | Ports |
|-----------|-------|-------|
| OTel Collector | `otel/opentelemetry-collector:latest` | 4317, 4318, 8888 |
| Jaeger | `jaegertracing/all-in-one:latest` | 16686, 6831 |
| Prometheus | `prom/prometheus:latest` | 9090 |
| Loki | `grafana/loki:latest` | 3100 |
| Grafana | `grafana/grafana:latest` | 3000 |