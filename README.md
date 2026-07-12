---
title: Multimodal RAG Thesis Backend
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# Multimodal RAG Thesis Backend

FastAPI backend for multimodal anatomy RAG system.

## Local setup (venv)

Use **Python 3.10 or 3.11** for this project (several ML pins do not support 3.13 yet). Always install with the venv’s interpreter so packages do not land in pyenv/system:

```bash
python3.10 -m venv .venv   # or python3.11
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

If you see paths like `~/.pyenv/versions/3.13...` during `pip install`, your shell is not using the venv. Check `which python` and `which pip` (both should be under `.../ThesisBackend/.venv/bin/`).

If **OpenCV** tries to compile from source and fails, the pinned `opencv-python-headless==4.8.1.78` in `requirements.txt` should install a **wheel**. If it still builds from source, run:

`python -m pip install --only-binary opencv-python-headless -r requirements.txt`

## MinIO (object storage for image links)

Image URLs in production are served from MinIO so links work even when the app runs on ephemeral or multi-replica setups.

### 1. Install and run MinIO (no install on your laptop; runs in Docker)

From the project root:

```bash
docker compose up -d minio
```

- **S3 API:** `http://localhost:9000`
- **Web console:** http://localhost:9001 (login: `minioadmin` / `minioadmin` unless you set `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`)

### 2. Install the Python client

```bash
pip install minio
```

(Or use the project’s `requirements.txt`, which includes `minio`.)

### 3. Environment

Copy `.env.example` to `.env` and set at least:

- **LM Studio (local LLM):** start a model in LM Studio → Developer → Local Server, then set:
  - `LLM_PROVIDER=lmstudio`
  - `LLM_API_BASE=http://127.0.0.1:1234/v1`
  - `LLM_MODEL=<model id shown in LM Studio>`
  - `LLM_ALLOW_ONLINE=false` (default — cloud LLMs are disabled)
- MinIO defaults work for local Docker: `MINIO_ENDPOINT=localhost:9000`, `MINIO_ACCESS_KEY=minioadmin`, `MINIO_SECRET_KEY=minioadmin`

Verify the LLM with `GET http://127.0.0.1:8000/debug/llm` (`lmstudio_reachable: true`).

To disable MinIO and use local `/outputs` only, set `MINIO_ENABLED=false`.

### 4. Using a MinIO license file (Enterprise / SUBNET)

If you have a MinIO license key file (e.g. from [SUBNET](https://subnet.min.io/)):

1. Save the license content to a file in the project, e.g. `minio.license` (keep it out of version control).
2. In `.env`, set the path:
   ```bash
   MINIO_LICENSE_FILE=./minio.license
   ```
3. In `docker-compose.yml`, uncomment the MinIO license volume so the container gets the file as `/minio.license`:
   ```yaml
   volumes:
     - minio_data:/data
     - ${MINIO_LICENSE_FILE:-./minio.license}:/minio.license:ro
   ```
4. Restart MinIO: `docker compose up -d minio`.

The standard open-source `minio/minio` image does not require a license; this is only for MinIO Enterprise/SUBNET deployments.

### 5. Flow

- **Upload PDF** → images are extracted, uploaded to MinIO, and indexed.
- **RAG ask** → returned image URLs are presigned MinIO links (or local `/outputs` if MinIO is off).

## Supabase Storage — debug upload pipeline

1. **Install the SDK** in the same environment as uvicorn: `pip install supabase` (also in `requirements.txt`).
2. **Preflight (no PDF):** `GET /debug/storage`  
   - Check `supabase_import_ok`, `supabase_client_ok`, `bucket_exists_in_project`, and `sample_object_keys`.
3. **Upload a PDF:** `POST /upload-pdf/`  
   - Response includes **`pipeline`**: steps 1–6 with `ok` and `detail` for each stage.
   - Step 4 includes **`extractor_stats`** (`uploads_ok`, `uploads_failed`, `failed_object_keys`).
4. **Server logs** — look for `[IMAGE_PIPELINE]` lines (steps 1–5).
5. If the bucket stays empty: fix step 2/4 `ok: false` and errors in `detail` before re-uploading.

## Blender MCP render integration (asset-based, no local backend storage)

RAG can optionally return a related 3D render URL from a remote Blender worker that renders pre-existing anatomy assets.

### `/rag/ask` new response fields

- `render_3d_url`: signed/public URL for the rendered anatomy image (when available)
- `render_3d_anatomy`: resolved anatomy key used for asset lookup (e.g. `brain`, `heart`, `spine`)

If no anatomy is detected or the Blender worker is unavailable, these fields are `null` and normal RAG still succeeds.

### Worker healthcheck endpoint

Use this backend route to verify MCP worker connectivity and contract URLs before testing RAG:

- `GET /blender/render-asset/healthcheck`

Example success:

```json
{
  "status": "ok",
  "configured": true,
  "blender_server_url": "http://blender-mcp:8001",
  "health_url": "http://blender-mcp:8001/health",
  "render_asset_url": "http://blender-mcp:8001/render-asset",
  "remote_health": {
    "status": "ok"
  },
  "error": null
}
```

Example when URL is missing:

```json
{
  "status": "error",
  "configured": false,
  "error": "BLENDER_SERVER_URL is not configured."
}
```

### Required environment

Set Blender worker base URL in `.env`:

```bash
BLENDER_SERVER_URL=http://<your-blender-worker-host>:<port>
```

The backend calls `POST {BLENDER_SERVER_URL}/render-asset` with an anatomy `asset_key` and `camera_preset`.
The worker should render from existing `.blend` assets and upload output to object storage, returning a URL.
