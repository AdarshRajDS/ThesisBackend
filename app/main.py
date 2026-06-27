import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import anatomy_mcp, rag, rag_experiment, visualize, grading, upload, blender

from app.api.routes import images
from app.api.routes import debug_storage



# ✅ Use persistent storage on HF, local folder otherwise
BASE_DATA_DIR = os.getenv("HF_HOME", ".")

OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "outputs")
REPO_ROOT = Path(__file__).resolve().parents[1]
ANATOMY_EXPORTS_DIR = REPO_ROOT / "anatomy_mcp" / "exports"
ANATOMY_VIEWER_DIR = REPO_ROOT / "anatomy_mcp" / "viewer"

# ✅ Create the folder BEFORE mounting
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANATOMY_EXPORTS_DIR, exist_ok=True)


app = FastAPI(title="Multimodal RAG API")

# CORS: comma-separated list in env, e.g.
# ALLOWED_ORIGINS=https://adarshds-thesisfrontend.hf.space,http://localhost:3000
origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

# Safe defaults for current frontend + local dev when env is not set
if not allowed_origins:
    allowed_origins = [
        "https://adarshds-thesisfrontend.hf.space",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag.router)
app.include_router(rag_experiment.router)
app.include_router(visualize.router)
app.include_router(grading.router)
app.include_router(upload.router)
app.include_router(images.router)
app.include_router(debug_storage.router)
app.include_router(blender.router)
app.include_router(anatomy_mcp.router)



# ✅ Mount the real path (not hardcoded "outputs")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount(
    "/anatomy-exports",
    StaticFiles(directory=str(ANATOMY_EXPORTS_DIR)),
    name="anatomy-exports",
)
app.mount(
    "/anatomy-viewer",
    StaticFiles(directory=str(ANATOMY_VIEWER_DIR), html=True),
    name="anatomy-viewer",
)


@app.get("/")
def root():
    return {"status": "running"}
