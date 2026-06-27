# Project Summary: Multimodal RAG Thesis Backend

## 1. Project Overview

This repository is a backend prototype for a multimodal Retrieval-Augmented Generation (RAG) system focused on anatomy content. It supports:

- PDF ingestion and image extraction
- text + image indexing
- question answering over multimodal content
- visualization / annotation
- on-demand Blender 3D asset generation through a separate Blender service

The system is built with:

- FastAPI for the main backend API
- A secondary FastAPI service for Blender generation
- Chroma as the vector store for embedding retrieval
- MinIO / Supabase as optional object storage for serving images and generated assets
- LangChain / CLIP / embedding models for multimodal retrieval and ranking

## 2. What the Project Does

### Core capabilities

- `POST /upload-pdf/`: ingest a PDF, extract images, upload them to object storage, and rebuild the multimodal index.
- `POST /rag/ask`: query the indexed corpus and receive an answer plus related image URLs.
- `POST /visualize/`: run a visualization pipeline to produce an annotated image.
- `POST /grade-annotation/`: grade annotation files uploaded by the user.
- `POST /blender/generate-brain-3d`: request 3D brain asset generation through the Blender service.

### Blender service behavior

- The `backend` API calls a separate `blender` service via `BLENDER_SERVER_URL`.
- The Blender service executes a script in headless Blender to generate a GLB model and an optional preview PNG.
- After generation, the backend uploads generated assets to MinIO/Supabase and returns signed URLs.

## 3. Repository Structure

- `app/`: FastAPI application, routes, service wrappers, schemas
- `src/`: core libraries for ingestion, embeddings, retrieval, multimodal RAG, Blender orchestration
- `docker-compose.yml`: orchestrates backend, blender service, and MinIO
- `Dockerfile`: builds the main backend image
- `Dockerfile.blender`: builds the Blender service image
- `requirements.txt`: Python dependencies
- `README.md`: project notes and local deployment instructions

## 4. API Endpoints

### `/` (GET)

- Root health endpoint from `app/main.py`
- Returns `{"status": "running"}`

### `/rag/ask` (POST)

- Request body: `AskRequest` with `question`
- Response: `AskResponse` with `answer` and optional `images`
- Implementation: `app/services/rag_service.py`
- Process:
  1. Retrieve text and image candidates from Chroma
  2. Build context for LLM answer
  3. Return answer + image list

### `/visualize/` (POST)

- Request body: `VisualizeRequest` with `question`
- Response: `VisualizeResponse` with `annotated_image`
- Implementation: `app/services/visualization_service.py`
- Process: forwards the request to `src.visualization.run_visual_answer`

### `/grade-annotation/` (POST)

- Upload a file via multipart form-data
- Response: `GradingResponse` with `score`, `feedback`, and `missing_structures`
- Implementation: `app/services/grading_service.py`

### `/upload-pdf/` (POST)

- Upload a PDF file
- Response: `IngestionResponse` containing ingestion pipeline details
- Implementation: `app/services/ingestion_service.py`
- Pipeline stages:
  1. Save PDF into `raw/`
  2. Storage preflight (`app/services/object_storage.py`)
  3. Text ingestion via `src.ingestion.run`
  4. Image extraction via `src.ingestion.run_image_extraction`
  5. Multimodal indexing via `src.multimodal.run_multimodal_indexing`
  6. RAG reload via `src.multimodal.run_multimodal_rag.reload_rag`
  7. Total runtime logging

### `/images/all` (GET)

- Lists local output images from `/outputs`
- Useful for debugging local image results

### `/debug/storage` (GET)

- Checks storage configuration for Supabase and MinIO
- Returns diagnostics including bucket status and sample keys
- Implementation: `app/services/object_storage.py`

### `/blender/generate-brain-3d` (POST)

- Request body: `GenerateBrain3DRequest`
- Response: `GenerateBrain3DResponse`
- Implementation: `app/services/blender_service.py`
- Behavior: calls remote Blender server at `BLENDER_SERVER_URL`
- Fallback: if `BLENDER_SERVER_URL` is unset, uses local `src.mcp.blender_mcp.BlenderMCP`

## 5. Key Internal Components

### `src/multimodal/multimodal_rag_chain.py`

- Creates `MultimodalRetriever`
- Uses `LLM` via `src.llm.llm_factory.get_llm()`
- Uses CLIP embedding for image reranking and text similarity
- Builds public image URLs via `app.services.object_storage.get_presigned_url`
- Falls back to local file URLs if storage signing is unavailable

### `src/multimodal/multimodal_retriever.py`

- Loads a Chroma collection named `multimodal_rag`
- Retrieves top documents and metadata
- Splits results between text docs and image candidates
- Applies a similarity cutoff to keep only relevant image metadata

### `src/ingestion/run.py`

- Loads PDFs using `DocumentLoader`
- Splits content into chunks
- Generates embeddings via `src.embeddings.embedding_factory`
- Adds chunks to a vector store created by `src.retrieval.vector_store.VectorStoreFactory`

### `src/mcp/blender_mcp.py`

- Orchestrates headless Blender execution
- Generates output paths under `outputs/blender`
- Validates prompt syntax and maps quality levels
- Runs Blender in background mode and returns task metadata

### `src/mcp/server.py`

- Exposes `/generate` on the Blender service container
- Calls `BlenderMCP.generate_3d_brain`
- Converts Blender result to HTTP response

## 6. Storage and Deployment

### MinIO

- Local object storage defined in `docker-compose.yml`
- Bucket name: `anatomy-images`
- Backend uploads generated assets and extracted image objects to MinIO
- Signed URLs are used to serve assets back to clients

### Supabase (optional)

- Code supports an alternate storage provider via `STORAGE_PROVIDER=supabase`
- `app/services/object_storage.py` handles Supabase upload and signed URLs
- `app/api/routes/debug_storage.py` checks Supabase readiness

### Docker

- `docker-compose.yml` defines three services:
  - `minio`
  - `backend`
  - `blender`
- `Dockerfile` builds the Python backend
- `Dockerfile.blender` builds a Blender service image with Blender installed and Python deps

## 7. Current Project Stage

### Working features

- Main backend API is implemented with route/service separation
- Blender service exists and is integrated via a remote HTTP call
- PDF ingestion pipeline is wired into text ingestion and multimodal index rebuild
- RAG and visualization entry points are present
- Object storage abstraction supports MinIO and Supabase

### Known issues / current blockers

- Blender service is returning `500 Internal Server Error` for `/generate`, likely because Blender headless execution in Docker is not yet stable or the subprocess args are not fully compatible.
- Local Blender process path and argument parsing require validation.
- Chroma schema version mismatch can occur if old database files remain after dependency upgrades.
- Some debug logs show the blender subprocess failing before the model is produced.

## 8. Recommended Next Steps

1. **Stabilize Blender service**
   - Confirm `Dockerfile.blender` installs Blender dependencies and Pillow into Blender's Python
   - Verify the command in `src/mcp/blender_mcp.py` uses the correct script path and that `blender_generator.py` parses `sys.argv` after `--`
   - Add container-level debug logging for Blender stdout/stderr

2. **Reset Chroma storage**
   - Remove incompatible old Chromadb directories under `data/processed/chroma` and `data/processed/multimodal_chroma`
   - Re-run ingestion to rebuild the vector store from scratch

3. **Add runtime health checks**
   - Validate `backend` can reach `blender` and `minio` at startup
   - Expose a dedicated `/health` endpoint for the backend

4. **Document usage clearly**
   - Add `README` run commands for both local and Docker-based testing
   - Provide sample `curl` requests for each API endpoint

5. **Test each endpoint manually**
   - `GET /debug/storage`
   - `POST /upload-pdf/`
   - `POST /rag/ask`
   - `POST /visualize/`
   - `POST /grade-annotation/`
   - `POST /blender/generate-brain-3d`

## 9. How to Explain the Project to Someone Else

### Short elevator pitch

This backend is a multimodal anatomy question-answering system that can ingest PDFs, index text and extracted images, answer questions with relevant context, and request 3D Blender asset generation for anatomy visualization.

### System role breakdown

- **Backend API** (`app/`): user-facing endpoints, orchestration logic, storage interaction.
- **Multimodal engine** (`src/`): ingestion, embeddings, vector retrieval, RAG answer assembly.
- **Blender microservice** (`src/mcp` + `Dockerfile.blender`): generates 3D models and preview images on demand.
- **Storage**: MinIO for assets and image links, with Supabase as an alternative provider.

### Deployment flow

1. Start storage and services with Docker Compose.
2. Upload PDFs to ingest text and images.
3. The system builds a Chroma index and a multimodal RAG instance.
4. Query the backend to receive answers plus image URLs.
5. Optionally request Blender-generated 3D models.

## 10. API Summary Table

| Endpoint                     | Method | Purpose                      | Main Handler                            | Output                 |
| ---------------------------- | ------ | ---------------------------- | --------------------------------------- | ---------------------- |
| `/`                          | GET    | Basic status                 | `app/main.py`                           | `status: running`      |
| `/rag/ask`                   | POST   | Ask a multimodal QA question | `app/services/rag_service.py`           | answer, images         |
| `/visualize/`                | POST   | Run visualization pipeline   | `app/services/visualization_service.py` | annotated image        |
| `/grade-annotation/`         | POST   | Grade an annotation upload   | `app/services/grading_service.py`       | score, feedback        |
| `/upload-pdf/`               | POST   | Ingest PDF and rebuild index | `app/services/ingestion_service.py`     | pipeline result        |
| `/images/all`                | GET    | List local output images     | route only                              | image URLs             |
| `/debug/storage`             | GET    | Storage diagnostics          | `app/services/object_storage.py`        | minio/supabase status  |
| `/blender/generate-brain-3d` | POST   | Create Blender 3D asset      | `app/services/blender_service.py`       | asset and preview URLs |

## 11. Workflow Diagram

```mermaid
flowchart TD
    A[User / Frontend] -->|Upload PDF| B[Backend API]
    B --> C[Save PDF to raw/]
    C --> D[Text ingestion pipeline]
    C --> E[Image extraction + upload]
    D --> F[Chroma text index]
    E --> G[Object storage (MinIO/Supabase)]
    F --> H[Multimodal RAG reload]
    H --> B

    B -->|Ask question| I[RAG Ask Endpoint]
    I --> J[MultimodalRetriever]
    J --> K[Chroma retrieval]
    K --> L[LLM answer generation]
    K --> M[CLIP image reranking]
    M --> G
    L --> I
    I --> A

    B -->|Generate 3D brain| N[Blender service]
    N --> O[Headless Blender script]
    O --> P[GLB + PNG outputs]
    P --> G
    P --> A
```

## 12. Suggested Document Naming and Testing Plan

Create this file as `PROJECT_SUMMARY.md` in the repo root. It can be used to onboard teammates or repeatedly explain the project.

### Test plan for repeating the setup

1. Clone repo.
2. Create `.env` from `.env.example` and set required values.
3. Run `docker compose up --build`.
4. Verify `minio`, `backend`, and `blender` are running.
5. Test `GET /debug/storage`.
6. Upload a PDF to `POST /upload-pdf/`.
7. Query `POST /rag/ask`.
8. Test Blender generation with `POST /blender/generate-brain-3d`.

## 13. Notes about the Current Blender Issue

The backend currently returns a `500` from the Blender service. The current repo state indicates problems with:

- Blender subprocess execution inside Docker
- path or argument parsing to `blender_generator.py`
- container-level dependency setup

Those should be the first debugging targets before confirming the system is fully end-to-end stable.

---

_Generated from repository inspection on April 2026._
