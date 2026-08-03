# ML Service — Integration Guide

> **Service:** ML / Vision API  
> **Version:** 1.0.0  
> **Port:** 8080 (internal); routed via Kong at `/ml`  
> **Language / Framework:** Python 3.11 · FastAPI · Ultralytics YOLOv8  
> **Database:** `mariadb-ml` (schema `ml_db`)  
> **Object Storage:** MinIO shared instance (buckets `ml`, `stream`)  
> **Messaging:** NATS (subject `detection.result`)  
> **Status:** Production-ready (Fase 5+)

---

## 1. Overview

The ML Service is a YOLOv8-based computer vision microservice. It owns a model registry (persisted in MariaDB), runs inference on images, and returns detections with bounding boxes. Results are stored in MinIO and published as events to NATS for downstream consumers (e.g., Alert Service, Dashboard).

### 1.1 Key Responsibilities
- **Model Registry** — register, list, update, activate, and delete YOLO weight files (`.pt`).
- **Inference** — accept images (multipart upload, base64 JSON, or MinIO object key from the `stream` bucket), run YOLO prediction, and return structured detections.
- **Artifact Storage** — persist original and annotated images to MinIO (`ml` bucket).
- **Event Publishing** — publish detection results to NATS (`detection.result`) so other services can react in real time.
- **History & Metrics** — store every inference run in MariaDB and expose Prometheus metrics.

### 1.2 Dependencies
| Dependency | Purpose | Notes |
|---|---|---|
| `mariadb-ml` | Persistent model registry + detection history | Schema auto-migrates on startup (`CREATE TABLE IF NOT EXISTS`) |
| `minio` | Object storage | Read from `stream` bucket; write to `ml` bucket |
| `nats` | Event bus | Publish-only (`detection.result`); failures are swallowed (best-effort) |
| `kong` | API Gateway | External traffic routed through Kong → `/ml` prefix |

---

## 2. REST API Endpoints

All routes are prefixed `/ml` (except `/health`). Responses follow the platform-standard envelope:

```jsonc
// Success (2xx)
{ "success": true, "data": { ... } }

// Error (4xx / 5xx)
{ "success": false, "error": { "code": "NOT_FOUND", "message": "..." } }
```

### 2.1 System Routes (Public — No JWT Required)

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/health` | Health check + model warm-up status | `HealthStatus` |

**`GET /health` response:**
```jsonc
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "ml-api",
    "version": "1.0.0",
    "models_loaded": 1,
    "default_model": "vision-aeroponik"
  }
}
```

### 2.2 Model Registry Routes (`/ml/models`)

Requires `read` role (`admin`, `operator`, `viewer`) for reads; `write` role (`admin`, `operator`) for mutations.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/ml/models` | Register a new model | write |
| `GET` | `/ml/models` | List all models (optional `?status_filter=active`) | read |
| `GET` | `/ml/models/{model_id}` | Get model details by ID or slug | read |
| `PUT` | `/ml/models/{model_id}` | Update model metadata | write |
| `POST` | `/ml/models/{model_id}/activate` | Set as default (active) model | write |
| `POST` | `/ml/models/{model_id}/weights` | Upload `.pt` weights file | write |
| `DELETE` | `/ml/models/{model_id}` | Delete model from registry | write |
| `GET` | `/ml/models/{model_id}/count` | Detection count for model | read |

**`POST /ml/models` request body (`ModelCreate`):**
```jsonc
{
  "name": "Vision Aeroponik v2",
  "slug": "vision-aeroponik-v2",
  "description": "Updated aeroponic detection model",
  "model_type": "yolov8",
  "framework": "ultralytics",
  "version": "v2.0",
  "file_path": "/app/models/best.pt",
  "class_names": ["plant", "leaf", "fruit"],
  "input_size": 640,
  "confidence_threshold": 0.25,
  "iou_threshold": 0.45,
  "is_default": false,
  "metadata": { "trained_on": "custom-dataset-v3" }
}
```

**`ModelOut` response fields:**
```jsonc
{
  "id": "uuid-string",
  "name": "Vision Aeroponik",
  "slug": "vision-aeroponik",
  "description": "...",
  "model_type": "yolov8",
  "framework": "ultralytics",
  "version": "v1.0",
  "file_path": "/app/models/vision-aeroponik.pt",
  "class_names": ["plant", "leaf"],
  "input_size": 640,
  "confidence_threshold": 0.25,
  "iou_threshold": 0.45,
  "status": "active",
  "is_default": true,
  "metadata": null,
  "loaded": true,
  "num_classes": 2,
  "created_at": "2026-07-21T04:00:00",
  "updated_at": "2026-07-21T04:00:00"
}
```

### 2.3 Inference Routes (`/ml/detect`, `/ml/detections`)

All inference endpoints require the `write` role. History listing requires the `read` role.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/ml/detect` | Run detection on uploaded image files (multipart) | write |
| `POST` | `/ml/detect/base64` | Run detection on a base64-encoded image (JSON body) | write |
| `POST` | `/ml/detect/from-stream` | Run detection on a frame already in MinIO `stream` bucket | write |
| `GET` | `/ml/detections` | Paginated history of inference runs | read |
| `GET` | `/ml/detections/{detection_id}` | Get a single detection record by DB ID | read |

**`POST /ml/detect` (multipart upload):**
- **Content-Type:** `multipart/form-data`
- **Form fields:**
  - `files` (required, array of `UploadFile`, max 16 MB each)
  - `model_id` (optional, string — omit to use default)
  - `conf` (optional, float 0.0–1.0)
  - `iou` (optional, float 0.0–1.0)
  - `imgsz` (optional, int > 0)

**`POST /ml/detect/base64` request body:**
```jsonc
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "model_id": "vision-aeroponik",
  "conf": 0.3,
  "iou": 0.45,
  "imgsz": 640
}
```

**`POST /ml/detect/from-stream` request body:**
```jsonc
{
  "object_key": "cctv-front/2026-07-21_120000_abc123_frame.jpg",
  "model_id": "vision-aeroponik",
  "conf": 0.3
}
```

**`DetectResponse` (inference result):**
```jsonc
{
  "count": 1,
  "results": [
    {
      "detection_uid": "uuid-string",
      "model_id": "vision-aeroponik",
      "model_name": "Vision Aeroponik",
      "source_type": "upload",
      "source_ref": "photo.jpg",
      "original_url": "http://localhost:9000/ml/original/20260721_120000_abc123_photo.jpg",
      "annotated_url": "http://localhost:9000/ml/detected/20260721_120000_abc123_photo.jpg",
      "num_detections": 3,
      "classes": ["plant", "fruit"],
      "detections": [
        {
          "class_id": 0,
          "class_name": "plant",
          "confidence": 0.89,
          "bbox": { "x1": 120, "y1": 45, "x2": 340, "y2": 210 }
        }
      ],
      "confidence_min": 0.65,
      "confidence_max": 0.89,
      "confidence_avg": 0.77,
      "execution_time_ms": 142.35,
      "status": "success"
    }
  ]
}
```

### 2.4 Results Routes (`/ml/results`)

These endpoints list and manage objects stored in the `ml` bucket (written by an external CCTV capture cron, not by the ML inference itself).

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/ml/results` | List objects under a prefix in `ml` bucket | read |
| `DELETE` | `/ml/results` | Delete a single object from `ml` bucket | write |

**`GET /ml/results` query params:**
- `prefix` (string, default `"frames"`) — one of `frames`, `annotated`, `results`
- `limit` (int, 1–1000, default 200)

**`ResultList` response:**
```jsonc
{
  "total": 42,
  "items": [
    {
      "key": "frames/20260721_120000_abc123_frame.jpg",
      "url": "/storage/ml/frames/20260721_120000_abc123_frame.jpg",
      "size": 245760,
      "last_modified": "2026-07-21T12:00:00",
      "kind": "frame"
    }
  ]
}
```

---

## 3. Input Contracts

The ML Service receives data from two primary sources:

### 3.1 From Stream Service (via MinIO)

The Stream Service writes snapshots and recordings to the `stream` bucket on the shared MinIO instance. The ML Service reads from this bucket in two ways:

1. **Explicit trigger via REST:** A client calls `POST /ml/detect/from-stream` with the `object_key` of a frame stored in the `stream` bucket.
2. **Implicit:** The external CCTV capture cron writes frames to the `ml` bucket, which the ML Service can list via `GET /ml/results?prefix=frames` (read-only listing for dashboard display).

### 3.2 From Dashboard / API Gateway (via Kong)

All REST API calls flow through Kong at the `/ml` prefix. Kong validates JWT tokens, applies rate limiting (300 req/min, 8000 req/hour), and forwards to the ML Service on port 8080.

Clients may send:
- Multipart image uploads (`POST /ml/detect`)
- Base64-encoded images (`POST /ml/detect/base64`)
- Model management requests (`POST /ml/models`, etc.)

### 3.3 Internal Startup Seeding

At startup, the service attempts to register a bundled weights file (`vision-aeroponik-model-root.pt`) as the default model if no default exists. The file must be present in the mounted `./volumes/ml-models:/app/models` volume.

---

## 4. Output Contracts

### 4.1 Detection Results (NATS Event)

After every successful inference, the service publishes a `detect.result` event to NATS:

- **Subject:** `detection.result` (configurable via `NATS_SUBJECT_DETECTION`)
- **Payload:** Full `DetectResult` dict serialized as JSON
- **Delivery:** Best-effort / fire-and-forget. If NATS is unavailable, the inference response still succeeds; the event is simply skipped and logged as a warning.

**Event payload shape:**
```jsonc
{
  "detection_uid": "uuid-string",
  "model_id": "vision-aeroponik",
  "model_name": "Vision Aeroponik",
  "source_type": "upload",
  "source_ref": "photo.jpg",
  "original_url": "http://localhost:9000/ml/original/20260721_120000_abc123_photo.jpg",
  "annotated_url": "http://localhost:9000/ml/detected/20260721_120000_abc123_photo.jpg",
  "num_detections": 3,
  "classes": ["plant", "fruit"],
  "detections": [
    {
      "class_id": 0,
      "class_name": "plant",
      "confidence": 0.89,
      "bbox": { "x1": 120, "y1": 45, "x2": 340, "y2": 210 }
    }
  ],
  "confidence_min": 0.65,
  "confidence_max": 0.89,
  "confidence_avg": 0.77,
  "execution_time_ms": 142.35,
  "status": "success"
}
```

Downstream consumers (e.g., Alert Service, WS-Gateway) should subscribe to `detection.result` to react in real time.

### 4.2 MinIO Storage

| Bucket | Prefix | Content | Written By |
|--------|--------|---------|-----------|
| `ml` | `original/` | Original input images (upload or stream frame) | ML Service |
| `ml` | `detected/` | Annotated images with bounding boxes drawn | ML Service |
| `ml` | `frames/` | Raw frames collected by external CCTV capture cron | External cron |
| `ml` | `annotated/` | Annotated frames from external pipeline | External cron |
| `ml` | `results/` | JSON result files from external pipeline | External cron |

### 4.3 MariaDB Persistence

Two tables are maintained in `mariadb-ml`:

- **`vision_models`** — model registry metadata
- **`vision_detections`** — one row per inference run (including detection UID, model ID, source type, URLs, detections JSON, confidence stats, execution time)

---

## 5. Integration Steps

### 5.1 Calling the ML Service from Another Microservice

1. **Route through Kong:** Always call `http://kong:8000/v1/ml/...` (or the external host). Do not call the ML Service container directly.
2. **Obtain a JWT:** Use the shared `JWT_SECRET` to request a token from the Auth Service (`POST /v1/auth/login`). The token must contain `roles` claims that include the required role (`admin` or `operator` for writes; `admin`, `operator`, or `viewer` for reads).
3. **Set the Authorization header:** `Authorization: Bearer <token>`
4. **Send the request:** Use the standard JSON envelope for responses.

**Example (Python):**
```python
import httpx

KONG_URL = "http://kong:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

headers = {"Authorization": f"Bearer {TOKEN}"}

# Trigger inference on a stream frame
resp = httpx.post(
    f"{KONG_URL}/v1/ml/detect/from-stream",
    json={
        "object_key": "cctv-front/2026-07-21_120000_abc123_frame.jpg",
        "model_id": "vision-aeroponik",
        "conf": 0.3
    },
    headers=headers,
    timeout=30.0,
)
resp.raise_for_status()
result = resp.json()["data"]
```

### 5.2 Consuming Detection Events (NATS)

Subscribe to `detection.result` to receive real-time inference outputs:

```python
import asyncio
import nats

async def main():
    nc = await nats.connect("nats://nats:4222")
    sub = await nc.subscribe("detection.result")
    async for msg in sub.messages:
        print(f"Detection: {msg.data.decode()}")

asyncio.run(main())
```

### 5.3 Writing Frames for ML Processing

If your service produces frames that should be analyzed by ML:

1. Upload the frame to MinIO `stream` bucket: `mc cp frame.jpg minio/stream/cctv-front/2026-07-21_frame.jpg`
2. Call `POST /ml/detect/from-stream` with the `object_key`.
3. Alternatively, upload the image directly via `POST /ml/detect` (multipart).

### 5.4 Registering a Custom Model

1. Ensure your `.pt` weights file is in the ML Service models volume (`./volumes/ml-models`).
2. Register the model: `POST /ml/models` with `file_path` pointing to the weights inside the container.
3. Or register first without weights, then upload: `POST /ml/models/{id}/weights`.
4. Activate: `POST /ml/models/{id}/activate`.
5. The model is now available for inference via `model_id`.

---

## 6. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | HTTP listen port |
| `DATABASE_URL` | `mysql+pymysql://app:app1234@mariadb-ml:3306/ml_db?charset=utf8mb4` | SQLAlchemy connection string |
| `JWT_SECRET` | `""` (must be set in prod) | Shared JWT secret with Auth Service |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `WRITE_ROLES` | `admin,operator` | Comma-separated roles allowed for write endpoints |
| `READ_ROLES` | `admin,operator,viewer` | Comma-separated roles allowed for read endpoints |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed browser origins |
| `MODELS_DIR` | `/app/models` | Directory for `.pt` weight files (mount a volume here) |
| `DEFAULT_WEIGHTS_FILENAME` | `best.pt` | Fallback filename searched when no explicit path is set |
| `AUTO_ACTIVATE_FIRST_MODEL` | `true` | Auto-activate the first registered model at startup |
| `DEFAULT_CONF_THRESHOLD` | `0.25` | Default YOLO confidence threshold |
| `DEFAULT_IOU_THRESHOLD` | `0.45` | Default YOLO IoU threshold |
| `DEFAULT_INPUT_SIZE` | `640` | Default YOLO input image size |
| `MAX_UPLOAD_MB` | `16` | Maximum upload size per image |
| `ALLOWED_IMAGE_EXTENSIONS` | `jpg,jpeg,png,bmp,webp` | Accepted image formats |
| `INFERENCE_TIMEOUT_SECONDS` | `30` | Wall-clock timeout per inference call |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO host:port |
| `MINIO_ACCESS_KEY` | `${MINIO_ML_ACCESS_KEY}` | MinIO access key (scoped for ML service) |
| `MINIO_SECRET_KEY` | `${MINIO_ML_SECRET_KEY}` | MinIO secret key (scoped for ML service) |
| `MINIO_USE_SSL` | `false` | Use TLS for MinIO connection |
| `MINIO_ML_BUCKET` | `ml` | Bucket for ML-originated images and external capture results |
| `MINIO_STREAM_BUCKET` | `stream` | Bucket for stream source frames (read) |
| `MINIO_ORIGINAL_PREFIX` | `original` | Prefix for original images in `ml` bucket |
| `MINIO_ANNOTATED_PREFIX` | `detected` | Prefix for annotated images in `ml` bucket |
| `MINIO_PUBLIC_URL` | `http://localhost:9000` | Public base URL for MinIO object links |
| `NATS_URL` | `nats://nats:4222` | NATS broker address |
| `NATS_USER` | `null` | Optional NATS username |
| `NATS_PASSWORD` | `null` | Optional NATS password |
| `NATS_SUBJECT_DETECTION` | `detection.result` | NATS subject for publishing detection events |
| `NATS_ENABLED` | `true` | Set to `false` to disable NATS publishing |

---

## 7. Model Registry Structure

### 7.1 Model States

| Status | Meaning |
|--------|---------|
| `registered` | Model entry exists in DB but weights are not yet loaded or uploaded |
| `active` | Model is loaded and ready for inference; can be the default |
| `failed` | Model failed to load (bad weights, incompatible format) |
| `disabled` | Model is intentionally disabled; cannot be used for inference |

### 7.2 Weight Resolution Order

When inference is requested, the engine resolves weights in this priority order:

1. Explicit `file_path` from model metadata (only if it resolves inside `/app/models`)
2. `/app/models/{model_id}.pt`
3. `/app/models/{slug}.pt`
4. `/app/models/best.pt` (fallback default)

All paths must resolve inside `MODELS_DIR` (`/app/models`). Arbitrary filesystem paths are rejected for security.

### 7.3 Default Model Selection

- Exactly one model can have `is_default = true`.
- If no default is set and `AUTO_ACTIVATE_FIRST_MODEL=true`, the oldest non-disabled model is promoted to default at startup.
- If no default exists and auto-activate is disabled, inference without `model_id` returns `404`.

### 7.4 Seeded Model

The service ships with a bundled root weights file (`vision-aeroponik-model-root.pt`) in `./models/`. At startup, if no model exists with id `vision-aeroponik`, the service registers it automatically:

- `model_id`: `vision-aeroponik`
- `slug`: `vision-aeroponik`
- `name`: `Vision Aeroponik`
- `description`: YOLO model for aeroponic plant/crop detection (user-triggered snapshots)

---

## 8. Example curl Commands

Replace `KONG_HOST`, `TOKEN`, and `MODEL_ID` as appropriate.

### 8.1 Health Check (Public)
```bash
curl -s http://localhost:8000/health | jq
```

### 8.2 Register a Model
```bash
curl -s -X POST http://localhost:8000/ml/models \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Model",
    "slug": "my-model",
    "description": "Custom YOLOv8 trained on aeroponic dataset",
    "version": "v1.0",
    "file_path": "/app/models/my-model.pt",
    "class_names": ["healthy", "diseased", "nutrient-deficiency"],
    "is_default": true
  }' | jq
```

### 8.3 List Models
```bash
curl -s http://localhost:8000/ml/models \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 8.4 Upload Weights
```bash
curl -s -X POST http://localhost:8000/ml/models/my-model/weights \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./my-model.pt"
```

### 8.5 Activate a Model
```bash
curl -s -X POST http://localhost:8000/ml/models/my-model/activate \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 8.6 Run Inference — Multipart Upload
```bash
curl -s -X POST http://localhost:8000/ml/detect \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@./frame.jpg" \
  -F "model_id=vision-aeroponik" \
  -F "conf=0.3" \
  -F "iou=0.45" | jq
```

### 8.7 Run Inference — Base64 JSON
```bash
curl -s -X POST http://localhost:8000/ml/detect/base64 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"$(base64 -w 0 ./frame.jpg)\",
    \"model_id\": \"vision-aeroponik\",
    \"conf\": 0.3
  }" | jq
```

### 8.8 Run Inference — From MinIO Stream Bucket
```bash
curl -s -X POST http://localhost:8000/ml/detect/from-stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "object_key": "cctv-front/2026-07-21_120000_abc123_frame.jpg",
    "model_id": "vision-aeroponik"
  }' | jq
```

### 8.9 List Detection History
```bash
curl -s "http://localhost:8000/ml/detections?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 8.10 Get Detection by ID
```bash
curl -s http://localhost:8000/ml/detections/1 \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 8.11 List Results (ml bucket)
```bash
curl -s "http://localhost:8000/ml/results?prefix=frames&limit=50" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 8.12 Delete a Result Object
```bash
curl -s -X DELETE "http://localhost:8000/ml/results?key=frames/old-frame.jpg" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 9. Prometheus Metrics

Exposed at `/metrics` and `/metrics-internal`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `vision_inferences_total` | Counter | `model_id`, `source_type`, `status` | Total inference requests processed |
| `vision_detections_total` | Counter | `model_id` | Total objects detected across all inferences |
| `vision_inference_seconds` | Histogram | `model_id` | Inference latency in seconds (buckets: 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0) |
| `vision_models_loaded` | Gauge | — | Number of YOLO models currently in memory |

---

## 10. Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `BAD_REQUEST` | Missing/invalid parameters (empty file, bad base64, invalid object key) |
| 401 | `UNAUTHORIZED` | Missing, expired, or invalid JWT |
| 403 | `FORBIDDEN` | Role not permitted for the requested operation |
| 404 | `NOT_FOUND` | Model not found, weights missing, frame not in stream bucket |
| 409 | `CONFLICT` | Model slug already exists |
| 413 | `PAYLOAD_TOO_LARGE` | Upload exceeds `MAX_UPLOAD_MB` |
| 422 | `BAD_REQUEST` | Validation error on request body |
| 429 | `TOO_MANY_REQUESTS` | Rate limited by Kong |
| 500 | `INTERNAL_ERROR` | Unhandled server error |
| 503 | `SERVICE_UNAVAILABLE` | JWT secret missing in non-development environment |

---

## 11. Observability & Resilience Notes

- **Graceful NATS failure:** If NATS is unreachable, inference responses are **not** blocked. Events are silently skipped and logged as warnings. Set `NATS_ENABLED=false` to fully disable publishing.
- **Inference timeout:** A hard wall-clock timeout (`INFERENCE_TIMEOUT_SECONDS`, default 30s) prevents a single request from hanging the worker thread. Exceeding the timeout returns `504 Gateway Timeout`.
- **Model warm-up:** The default model is loaded into memory at startup. Additional models are loaded lazily on first inference request and cached in memory.
- **Concurrency:** Inference runs in a dedicated thread pool (`max_workers=2`) so long-running predictions do not block the async event loop.

---

## 12. File Layout Reference

```
services/ml/
├── Dockerfile
├── requirements.txt
├── models/
│   ├── .gitkeep
│   └── vision-aeroponik-model-root.pt   # pre-seeded root weights
├── tests/
│   ├── test_detect_shape.py
│   ├── test_registry.py
│   └── test_storage.py
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI app factory, startup hooks
    ├── config.py             # Pydantic Settings (env vars)
    ├── database.py           # SQLAlchemy models (VisionModel, VisionDetection) + init_db
    ├── schemas.py            # Pydantic request/response schemas
    ├── security.py           # JWT auth dependency (shared secret with Auth Service)
    ├── responses.py          # Standardized JSON envelope wrapper
    ├── routes_system.py      # GET /health
    ├── routes_models.py      # /ml/models CRUD + weights upload + activate
    ├── routes_detect.py      # /ml/detect, /ml/detect/base64, /ml/detect/from-stream, /ml/detections
    ├── routes_results.py     # /ml/results (list/delete from ml bucket)
    ├── vision_engine.py      # ModelRegistry + YOLO inference engine
    ├── storage.py            # MinIO client wrapper
    ├── messaging.py          # NATS publisher (detection.result)
    └── metrics.py            # Prometheus counters, histograms, gauges
```
