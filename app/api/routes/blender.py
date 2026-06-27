from fastapi import APIRouter

from app.schemas.blender import GenerateBrain3DRequest, GenerateBrain3DResponse
from app.services.blender_service import (
    blender_render_worker_healthcheck,
    generate_brain_3d,
)

router = APIRouter(prefix="/blender", tags=["Blender"])


@router.post("/generate-brain-3d", response_model=GenerateBrain3DResponse)
def generate_brain(req: GenerateBrain3DRequest):
    return generate_brain_3d(req)


@router.get("/health")
def health():
    return {"service": "blender", "status": "ok"}


@router.get("/render-asset/healthcheck")
def render_asset_healthcheck():
    """
    Backend-side connectivity check for remote Blender worker endpoint used by RAG.
    """
    return blender_render_worker_healthcheck()
