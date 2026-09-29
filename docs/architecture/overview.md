# Architecture Overview

## System Context

PokéX is a distributed system for Pokémon TCG card data management. Five independently deployable services communicate via REST APIs and shared infrastructure.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Web App   │◄───►│  Data Ingestion  │◄───►│ PostgreSQL  │
│  (React 19) │     │   (FastAPI)      │     │   (16)      │
│  Port 3000  │     │    Port 8000     │     │  Port 5432  │
└─────────────┘     └────────┬─────────┘     └─────────────┘
                             │
                    ┌────────┼─────────┐
                    │        │         │
                    ▼        ▼         ▼
             ┌──────────┐ ┌────────┐ ┌────────┐
             │ MinIO    │ │ Redis  │ │Scraper │
             │ (S3 API) │ │ (Cache)│ │Port 8002│
             └──────────┘ └────────┘ └────────┘
                    ▲                         ▲
                    │                         │
             ┌──────┴──────┐           ┌──────┴──────┐
             │ Recognition │           │  JustTCG    │
             │  (YOLOv8)   │           │   API       │
             │  Port 8001  │           └─────────────┘
             └─────────────┘
```

## Service Boundaries

| Service | Responsibility | Data Ownership | Scaling |
|---------|---------------|----------------|---------|
| Data Ingestion | CRUD for sets, cards, prices; image upload | PostgreSQL (sets, cards, prices, images) | Horizontal (stateless) |
| Recognition | Card detection (YOLOv8 ONNX) + OCR fallback | None (stateless inference) | Horizontal (GPU optional) |
| Scraper | Sync JustTCG API → PostgreSQL | Write-only to PostgreSQL | Single instance (rate limited) |
| Web | Browser UI: Sets, Scan, Collection | Read-only (React Query cache) | Horizontal (static files) |
| Desktop-Mobile | Offline-first native app | Local SQLite (libsql) | N/A (client) |

## Communication Patterns

### Synchronous (REST)

```
Web App ──GET /api/sets──────► Data Ingestion
Web App ──POST /recognize────► Recognition
Scraper ──POST /cards───────► Data Ingestion
Desktop ──GET /sync─────────► Data Ingestion
```

### Asynchronous (Redis Pub/Sub)

```
Data Ingestion ──INVALIDATE "cards"──► Redis
Web App ◄──SUBSCRIBE "cards"──────── Redis (React Query invalidation)
Desktop ◄──SUBSCRIBE "cards"──────── Redis (local cache invalidation)
```

## Data Models

### Core Entities

```typescript
// Shared conceptual model (inlined per service)
interface Set {
  id: string;           // e.g. "sv01"
  name: string;         // "Scarlet & Violet"
  series: string;       // "Scarlet & Violet"
  printedTotal: number;
  total: number;
  releaseDate: string;  // ISO 8601
  images: { symbol: string; logo: string };
}

interface Card {
  id: string;           // e.g. "sv01-1"
  name: string;         // "Pikachu"
  setId: string;        // FK → Set.id
  number: string;       // "1/198"
  rarity: string;       // "Common", "Rare", etc.
  images: { small: string; large: string };
  types: string[];      // ["Lightning"]
  hp?: number;
  artist?: string;
}

interface Price {
  cardId: string;       // FK → Card.id
  source: string;       // "tcgplayer", "ebay", "cardmarket"
  price: number;        // USD cents
  currency: string;     // "USD"
  updatedAt: Date;
}
```

### Recognition Types (Python/Rust)

```python
# Python (recognition_app/detector/detector.py)
class DetectionResult:
    bbox: tuple[float, float, float, float]  # x, y, w, h normalized
    confidence: float
    class_id: int
    class_name: str  # "card", "energy", "trainer"

class OCRResult:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]
```

```rust
// Rust (desktop-mobile/src-tauri/src/recognition.rs)
pub struct CardDetection {
    pub bbox: (f32, f32, f32, f32),
    pub confidence: f32,
    pub label: String,
}
```

## Infrastructure

### PostgreSQL (Data Ingestion)

- Schema: `sets`, `cards`, `prices`, `images` tables
- Migrations: Alembic (versioned in `services/data-ingestion/alembic/`)
- Connection: asyncpg + SQLAlchemy 2.0 async
- Pooling: Built-in SQLAlchemy pool (default 5 + overflow)

### Redis (Cache & Invalidation)

- Port: 6379
- Usage: HTTP cache (ETag/Cache-Control middleware), Pub/Sub for cache invalidation across services, session storage (future)
- Persistence: AOF enabled

### MinIO (Object Storage)

- Ports: 9000 (API), 9001 (Console)
- Bucket: `pokemon-cards`
- Usage: Card image storage (original + thumbnails)
- Access: S3-compatible API via boto3

## Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│                    OTel Collector                         │
├─────────┬─────────┬─────────┬─────────┬─────────────────┤
│ Traces  │ Metrics │ Logs    │ Profiles│  Exporters      │
│ (Jaeger)│(Prom.)  │(Loki)   │(Pyroscope)│                │
└────┬────┴────┬────┴────┬────┴────┬────┴────────────────┘
     │         │         │         │
     ▼         ▼         ▼         ▼
┌─────────────────────────────────────────────────────────┐
│                    Grafana Dashboards                     │
└─────────────────────────────────────────────────────────┘
```

### Instrumentation

| Service | Traces | Metrics | Logs |
|---------|--------|---------|------|
| Data Ingestion | FastAPI auto | Prometheus client | structlog |
| Recognition | Manual spans | Custom counters | structlog |
| Scraper | FastAPI auto | Prometheus client | structlog |
| Web | React Query devtools | — | Console |
| Desktop | — | — | tracing (Rust) |

## Security

- Network: Services communicate via Docker network; only web/recognition exposed
- Auth: API keys via env vars (JustTCG); no service-to-service auth yet
- Secrets: Docker secrets / GitHub Actions secrets for CI
- CORS: Configured per service (web origin allowed)
- Rate Limiting: Not implemented (TODO)

## Scaling Considerations

| Bottleneck | Current | Mitigation |
|------------|---------|------------|
| Recognition (CPU) | Single worker | Horizontal + GPU (ONNX CUDA) |
| Scraper (rate limit) | Sequential | Async batch + respect Retry-After |
| PostgreSQL writes | Single writer | Read replicas + connection pooling |
| Redis memory | Unbounded | TTL policies + maxmemory |
| Image processing | Sync in request | Offload to background workers |

## Evolution Path

1. **v0 (Current)**: Monorepo, Docker Compose, manual deploy
2. **v1**: Kubernetes (Helm), GitOps (ArgoCD), service mesh
3. **v2**: Event-driven (Kafka), CQRS for read models, multi-region