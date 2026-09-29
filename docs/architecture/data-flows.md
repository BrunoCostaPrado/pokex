# Data Flow Diagrams

## Full System Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  JustTCG    │────►│   Scraper    │────►│  PostgreSQL │
│    API      │     │  (Port 8002) │     │  (Port 5432)│
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                        ┌──────────────┐         │
                        │ Data Ingestion│◄────────┘
                        │  (Port 8000) │
                        └──────┬───────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
          ┌──────────┐  ┌──────────┐  ┌──────────┐
          │   Web    │  │ Desktop  │  │Recognition│
          │ (Port3000)│  │  (Tauri) │  │(Port 8001)│
          └──────────┘  └──────────┘  └──────────┘
                 ▲             ▲
                 │             │
                 └──────┬──────┘
                        ▼
                 ┌──────────┐
                 │  Redis   │
                 │(Port 6379)│
                 └──────────┘
```

## Scraper → Data Ingestion → PostgreSQL

```mermaid
sequenceDiagram
    participant S as Scraper
    participant J as JustTCG API
    participant D as Data Ingestion
    participant P as PostgreSQL
    participant R as Redis
    
    S->>J: GET /sets
    J-->>S: Set[]
    S->>D: POST /api/v1/sets (bulk)
    D->>P: INSERT ... ON CONFLICT UPDATE
    P-->>D: OK
    D-->>S: 201 Created
    
    loop For each set
        S->>J: GET /cards/{set_id}
        J-->>S: Card[]
        S->>D: POST /api/v1/cards (bulk)
        D->>P: INSERT ... ON CONFLICT UPDATE
    end
    
    loop For each card
        S->>J: GET /prices/{card_id}
        J-->>S: Price[]
        S->>D: POST /api/v1/prices (bulk)
        D->>P: INSERT ... ON CONFLICT UPDATE
    end
    
    D->>R: PUBLISH "cards" INVALIDATE
    R-->>Web: SUBSCRIBE "cards" → invalidate React Query
    R-->>Desktop: SUBSCRIBE "cards" → invalidate moka cache
```

## Web App: Set Browse Flow

```mermaid
sequenceDiagram
    participant U as User
    participant W as Web App
    participant Q as TanStack Query
    participant D as Data Ingestion
    participant P as PostgreSQL
    participant R as Redis
    
    U->>W: Navigate to /sets
    W->>Q: useQuery(['sets'], fetchSets)
    Q->>D: GET /api/v1/sets?page=1&limit=50
    D->>R: Check ETag cache
    alt Cache HIT
        R-->>D: 304 Not Modified
        D-->>Q: 304 (cached body)
    else Cache MISS
        D->>P: SELECT * FROM sets LIMIT 50
        P-->>D: Set[]
        D->>R: SET cache with ETag
        D-->>Q: 200 OK + ETag
    end
    Q-->>W: Set[] (cached)
    W-->>U: Render set grid
```

## Recognition Pipeline

```mermaid
sequenceDiagram
    participant U as User (Web/Desktop)
    participant R as Recognition Service
    participant M as MinIO
    participant O as ONNX Runtime
    participant E as EasyOCR
    participant T as pytesseract
    
    U->>R: POST /recognize (multipart image)
    R->>M: Store original image
    R->>O: preprocess(image) → 320x320 tensor
    O-->>R: [1, 84, 8400] raw output
    R->>R: NMS (IoU 0.45, conf 0.25)
    R->>R: Filter classes: card, energy, trainer
    
    loop For each detection
        R->>R: crop(image, bbox)
        R->>E: recognize(crop)
        alt EasyOCR success
            E-->>R: text + confidence
        else EasyOCR low confidence
            R->>T: recognize(crop)
            T-->>R: text + confidence
        end
    end
    
    R-->>U: { detections[], ocr_results[], processing_time_ms }
```

## Cache Invalidation Flow

```mermaid
sequenceDiagram
    participant D as Data Ingestion
    participant R as Redis
    participant W as Web App (React Query)
    participant M as Desktop (moka)
    
    D->>D: POST /api/v1/cards (write)
    D->>P: UPDATE cards SET ...
    D->>R: PUBLISH "cards" "INVALIDATE"
    
    par Web Invalidation
        R-->>W: MESSAGE "cards" "INVALIDATE"
        W->>Q: queryClient.invalidateQueries({ queryKey: ['cards'] })
        Q->>D: GET /api/v1/cards (refetch)
    and Desktop Invalidation
        R-->>M: MESSAGE "cards" "INVALIDATE"
        M->>M: mokaCache.invalidate("cards")
        M->>D: GET /api/v1/cards (next request)
    end
```

## Desktop Sync Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend (React)
    participant B as Backend (Rust)
    participant S as SQLite (libsql)
    participant D as Data Ingestion API
    participant R as Redis
    
    U->>F: Click "Sync Now"
    F->>B: invoke("sync_full")
    B->>D: GET /api/v1/sets
    D-->>B: Set[]
    B->>S: REPLACE INTO sets ...
    
    loop For each set
        B->>D: GET /api/v1/cards?set_id={id}
        D-->>B: Card[]
        B->>S: REPLACE INTO cards ...
    end
    
    B->>D: GET /api/v1/prices
    D-->>B: Price[]
    B->>S: REPLACE INTO prices ...
    
    B->>S: UPDATE sync_state SET value=now() WHERE key='last_sync'
    B-->>F: SyncResult { sets: 12, cards: 15000, prices: 45000 }
    F-->>U: Toast "Sync complete"
```

## Image Upload Flow

```mermaid
sequenceDiagram
    participant U as User
    participant W as Web App
    participant D as Data Ingestion
    participant M as MinIO
    participant P as PostgreSQL
    
    U->>W: Select image file
    W->>D: POST /api/v1/cards/{id}/image (multipart)
    D->>M: PUT object (key: cards/{id}/{uuid}.webp)
    M-->>D: OK
    D->>P: INSERT INTO images (card_id, object_key, ...)
    P-->>D: OK
    D-->>W: { image_url: "https://minio/.../cards/{id}/{uuid}.webp" }
    W-->>U: Show uploaded image
```

## Error Handling Flows

### Recognition Failure

```
POST /recognize
    │
    ├─► Image decode error → 400 Bad Request { "error": "Invalid image format" }
    │
    ├─► ONNX inference error → 500 Internal Server Error { "error": "Model inference failed" }
    │
    ├─► OCR timeout (30s) → 504 Gateway Timeout { "error": "OCR processing timeout" }
    │
    └─► Success → 200 OK { detections: [...], ocr_results: [...] }
```

### Scraper Rate Limit

```
GET /cards/{set_id}
    │
    ├─► 429 Too Many Requests → wait Retry-After header → retry (max 3)
    │
    ├─► 5xx Server Error → exponential backoff → retry (max 3)
    │
    └─► Success → process cards
```

### Database Connection Failure

```
Any DB operation
    │
    ├─► Connection pool exhausted → 503 Service Unavailable
    │
    ├─► Query timeout (30s) → 504 Gateway Timeout
    │
    └─► Constraint violation → 409 Conflict { "error": "Duplicate key" }
```