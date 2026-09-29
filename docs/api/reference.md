# API Reference

## Base URLs

| Environment | Data Ingestion | Recognition | Scraper | Web |
|-------------|----------------|-------------|---------|-----|
| Local | `http://localhost:8000` | `http://localhost:8001` | `http://localhost:8002` | `http://localhost:3000` |
| Docker | `http://data-ingestion:8000` | `http://recognition:8001` | `http://scraper:8002` | `http://web:3000` |
| Prod | `https://api.pokex.dev` | `https://recognition.pokex.dev` | Internal only | `https://pokex.dev` |

## Authentication

Currently: API keys via environment variables only.
- `JUSTTCG_API_KEY` for Scraper → JustTCG
- No service-to-service auth (TODO: mTLS or shared secrets)

Future: JWT Bearer tokens for user-facing endpoints.

---

## Data Ingestion Service (Port 8000)

### Health Check

```http
GET /health
```

**Response 200**
```json
{
  "status": "healthy",
  "service": "data-ingestion",
  "version": "0.1.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "minio": "ok"
  }
}
```

### Sets

#### List Sets
```http
GET /api/v1/sets?page=1&limit=50&series=Scarlet&Violet
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `limit` | integer | 50 | Items per page (max 100) |
| `series` | string | — | Filter by series name |
| `search` | string | — | Search in name/id |

**Response 200**
```json
{
  "data": [
    {
      "id": "sv01",
      "name": "Scarlet & Violet",
      "series": "Scarlet & Violet",
      "printedTotal": 198,
      "total": 198,
      "releaseDate": "2023-03-31",
      "images": {
        "symbol": "https://minio/.../sv01/symbol.png",
        "logo": "https://minio/.../sv01/logo.png"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 12,
    "totalPages": 1
  }
}
```

**Headers**
```
ETag: "abc123"
Cache-Control: public, max-age=300, stale-while-revalidate=60
```

#### Get Set
```http
GET /api/v1/sets/{id}
```

**Response 200** — Same as list item

**Response 404**
```json
{ "detail": "Set not found" }
```

#### Create Set
```http
POST /api/v1/sets
Content-Type: application/json

{
  "id": "sv08",
  "name": "Surging Sparks",
  "series": "Scarlet & Violet",
  "printedTotal": 191,
  "total": 191,
  "releaseDate": "2024-11-08",
  "images": {
    "symbol": "https://.../symbol.png",
    "logo": "https://.../logo.png"
  }
}
```

**Response 201** — Created set object

#### Update Set
```http
PATCH /api/v1/sets/{id}
Content-Type: application/json

{
  "name": "Updated Name",
  "total": 200
}
```

#### Delete Set
```http
DELETE /api/v1/sets/{id}
```

**Response 204** — No content

---

### Cards

#### List Cards
```http
GET /api/v1/cards?page=1&limit=50&set_id=sv01&rarity=Rare&type=Fire
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `limit` | integer | Items per page (max 100) |
| `set_id` | string | Filter by set |
| `rarity` | string | Filter by rarity |
| `type` | string | Filter by Pokémon type |
| `search` | string | Search name/number |

**Response 200**
```json
{
  "data": [
    {
      "id": "sv01-1",
      "name": "Pikachu",
      "setId": "sv01",
      "number": "1/198",
      "rarity": "Common",
      "images": {
        "small": "https://minio/.../sv01-1/small.webp",
        "large": "https://minio/.../sv01-1/large.webp"
      },
      "types": ["Lightning"],
      "hp": 60,
      "artist": "Kouki Saitou"
    }
  ],
  "pagination": { ... }
}
```

#### Get Card
```http
GET /api/v1/cards/{id}
```

#### Create Card
```http
POST /api/v1/cards
Content-Type: application/json

{
  "id": "sv08-150",
  "name": "Charizard ex",
  "setId": "sv08",
  "number": "150/191",
  "rarity": "Double Rare",
  "images": { "small": "...", "large": "..." },
  "types": ["Fire"],
  "hp": 330,
  "artist": "PLANETA Mochizuki"
}
```

#### Get Card Image
```http
GET /api/v1/cards/{id}/image?size=large
```

| Parameter | Values | Default |
|-----------|--------|---------|
| `size` | `small` \| `large` | `large` |

**Response 302** — Redirects to MinIO presigned URL

**Response 404** — Image not found

#### Upload Card Image
```http
POST /api/v1/cards/{id}/image
Content-Type: multipart/form-data

file: <image file> (max 10MB, webp/png/jpg)
```

**Response 201**
```json
{
  "imageUrl": "https://minio/.../cards/sv01-1/abc123.webp",
  "size": "large"
}
```

---

### Prices

#### List Prices
```http
GET /api/v1/prices?card_id=sv01-1&source=tcgplayer
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `card_id` | string | Filter by card |
| `source` | string | Filter by price source |

**Response 200**
```json
{
  "data": [
    {
      "cardId": "sv01-1",
      "source": "tcgplayer",
      "price": 125,  // USD cents
      "currency": "USD",
      "updatedAt": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Get Prices for Card
```http
GET /api/v1/prices/{card_id}
```

---

## Recognition Service (Port 8001)

### Health Check

```http
GET /health
```

**Response 200**
```json
{
  "status": "healthy",
  "service": "recognition",
  "version": "0.1.0",
  "model": "yolov8n_card.onnx",
  "checks": { "model": "loaded", "minio": "ok" }
}
```

### Recognize Single Image

```http
POST /recognize
Content-Type: multipart/form-data

file: <image file> (max 10MB)
```

**Response 200**
```json
{
  "detections": [
    {
      "bbox": [0.12, 0.23, 0.75, 0.68],
      "confidence": 0.94,
      "class_id": 0,
      "class_name": "card"
    },
    {
      "bbox": [0.45, 0.60, 0.15, 0.12],
      "confidence": 0.87,
      "class_id": 1,
      "class_name": "energy"
    }
  ],
  "ocr_results": [
    {
      "text": "Pikachu",
      "confidence": 0.91,
      "bbox": [0.15, 0.25, 0.30, 0.08]
    },
    {
      "text": "60 HP",
      "confidence": 0.88,
      "bbox": [0.15, 0.35, 0.20, 0.05]
    }
  ],
  "processing_time_ms": 142
}
```

**Response 400**
```json
{ "detail": "Invalid image format. Supported: JPEG, PNG, WebP" }
```

**Response 413** — File too large (>10MB)

**Response 500** — Model inference error

---

### Batch Recognition

```http
POST /recognize/batch
Content-Type: multipart/form-data

files: <image files[]> (max 10, each max 10MB)
```

**Response 200**
```json
{
  "results": [
    { "index": 0, "detections": [...], "ocr_results": [...], "processing_time_ms": 142 },
    { "index": 1, "detections": [...], "ocr_results": [...], "processing_time_ms": 138 }
  ],
  "total_time_ms": 280
}
```

---

## Scraper Service (Port 8002)

### Health Check

```http
GET /health
```

### Sync Endpoints

#### Full Set Sync
```http
POST /sync/sets
```

**Response 202**
```json
{ "status": "started", "task_id": "sync_sets_abc123" }
```

#### Full Card Sync
```http
POST /sync/cards
```

#### Full Price Sync
```http
POST /sync/prices
```

#### Full Pipeline
```http
POST /sync/all
```

**Response 202**
```json
{ "status": "started", "task_id": "sync_all_xyz789", "estimated_duration_minutes": 15 }
```

#### Incremental Sync
```http
POST /sync/incremental
Content-Type: application/json

{
  "since": "2024-01-15T00:00:00Z"
}
```

---

## WebSocket / Server-Sent Events (Future)

### Cache Invalidation Stream

```http
GET /events/cache
Accept: text/event-stream
```

**Event Stream**
```
event: invalidate
data: {"entity": "cards", "action": "invalidate"}

event: invalidate
data: {"entity": "sets", "action": "invalidate"}
```

---

## Error Responses

All services use standard FastAPI error format:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async) |
| 204 | No Content |
| 302 | Redirect (image URLs) |
| 304 | Not Modified (ETag) |
| 400 | Bad Request |
| 401 | Unauthorized (future) |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 413 | Payload Too Large |
| 422 | Validation Error |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |
| 504 | Gateway Timeout |

---

## Rate Limits (Current)

| Service | Limit | Window |
|---------|-------|--------|
| Data Ingestion | 1000 req/min | Per IP |
| Recognition | 60 req/min | Per IP |
| Scraper | N/A (internal) | — |

---

## OpenAPI Specs

Available at:
- Data Ingestion: `http://localhost:8000/openapi.json`
- Recognition: `http://localhost:8001/openapi.json`
- Scraper: `http://localhost:8002/openapi.json`

Swagger UI: `/docs` on each service.
ReDoc: `/redoc` on each service.