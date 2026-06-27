import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services.object_storage import get_presigned_url, put_object
from app.schemas.blender import GenerateBrain3DRequest
from src.config.settings import settings
from src.mcp.blender_mcp import BlenderMCP


def blender_render_worker_healthcheck() -> Dict[str, Any]:
    """
    Check whether remote Blender worker for asset rendering is reachable.
    """
    base = (settings.blender_server_url or "").strip().rstrip("/")
    if not base:
        return {
            "status": "error",
            "configured": False,
            "error": "BLENDER_SERVER_URL is not configured.",
        }

    out: Dict[str, Any] = {
        "status": "error",
        "configured": True,
        "blender_server_url": base,
        "health_url": f"{base}/health",
        "render_asset_url": f"{base}/render-asset",
        "remote_health": None,
        "error": None,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(out["health_url"])
        response.raise_for_status()
        out["remote_health"] = response.json() if response.content else {}
        out["status"] = "ok"
    except Exception as exc:
        out["error"] = f"Blender worker unreachable: {exc}"
    return out


def _to_object_key(path: Path, prefix: str = "blender") -> str:
    filename = path.name
    return f"{prefix}/{filename}"


def _upload_file(path: Path, content_type: str) -> Optional[str]:
    if not path.exists():
        return None

    object_key = _to_object_key(path)
    data = path.read_bytes()
    uploaded = put_object(object_key, data, content_type=content_type)
    if uploaded:
        return get_presigned_url(object_key)
    return None


def _call_remote_blender(request: GenerateBrain3DRequest) -> Dict[str, Any]:
    if not settings.blender_server_url:
        return {"status": "error", "error": "Blender server URL is not configured."}

    payload = request.model_dump()
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{settings.blender_server_url.rstrip('/')}/generate",
                json=payload,
            )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"status": "error", "error": f"Blender service error: {exc}"}


def generate_brain_3d(request: GenerateBrain3DRequest) -> Dict[str, Any]:
    if not request.prompt or len(request.prompt.strip()) < 10:
        return {
            "status": "error",
            "error": "Prompt must be at least 10 characters and describe a brain anatomy view.",
        }

    if settings.blender_server_url:
        result = _call_remote_blender(request)
    else:
        blender = BlenderMCP()
        result = blender.generate_3d_brain(
            request.prompt,
            request.quality,
            request.format,
            request.include_preview,
        )

    if result.get("status") != "generated":
        return {
            "status": "error",
            "error": result.get("error", "Blender generation failed."),
        }

    task_id = result.get("task_id")

    model_path_str = result.get("model_path")
    if not model_path_str:
        return {"status": "error", "error": "Blender returned no model path."}
    model_path = Path(model_path_str)
    preview_path = Path(result.get("preview_path")) if result.get("preview_path") else None

    asset_url = _upload_file(model_path, mimetypes.guess_type(model_path.name)[0] or "application/octet-stream")
    preview_url = None
    warnings = []

    if preview_path is not None and preview_path.exists():
        preview_url = _upload_file(preview_path, "image/png")
        if not preview_url:
            warnings.append("Preview image generated but upload failed; serving local preview instead.")
            preview_url = f"/outputs/blender/{preview_path.name}" if preview_path.exists() else None

    if not asset_url:
        warnings.append("Asset generated but upload failed; serving local file instead.")
        asset_url = f"/outputs/blender/{model_path.name}" if model_path.exists() else None

    return {
        "status": "generated",
        "asset_url": asset_url,
        "preview_url": preview_url,
        "task_id": task_id,
        "warnings": warnings or None,
    }


# -------- RAG-linked asset rendering (MCP-style remote worker, no local backend storage) --------

ASSET_MAPPING: Dict[str, Dict[str, str]] = {
    "brain": {"asset_key": "brain", "camera_preset": "frontal-superior"},
    "heart": {"asset_key": "heart", "camera_preset": "lateral"},
    "hand": {"asset_key": "hand", "camera_preset": "dorsal"},
    "lung": {"asset_key": "lung", "camera_preset": "anterior"},
    "spine": {"asset_key": "spine", "camera_preset": "posterior"},
}

ANATOMY_SYNONYMS: Dict[str, str] = {
    "brain": "brain",
    "cerebrum": "brain",
    "cerebral": "brain",
    "cortex": "brain",
    "heart": "heart",
    "cardiac": "heart",
    "hand": "hand",
    "palm": "hand",
    "lung": "lung",
    "lungs": "lung",
    "pulmonary": "lung",
    "spine": "spine",
    "spinal": "spine",
    "vertebra": "spine",
    "vertebrae": "spine",
}


def _extract_anatomy_key(question: str, answer: str = "", sources: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Resolve one anatomy key from question/answer/sources.
    """
    source_text = ""
    if sources:
        source_text = " ".join((s.get("chunk_preview") or "") for s in sources if isinstance(s, dict))
    combined = f"{question}\n{answer}\n{source_text}".lower()

    # deterministic ordering prioritizes explicit target list
    for token, key in ANATOMY_SYNONYMS.items():
        if token in combined:
            return key
    return None


def _call_remote_asset_render(asset_key: str, camera_preset: str, request_id: str) -> Dict[str, Any]:
    if not settings.blender_server_url:
        return {"status": "error", "error": "Blender server URL is not configured."}

    payload = {
        "asset_key": asset_key,
        "camera_preset": camera_preset,
        "request_id": request_id,
        "output_format": "png",
        # worker is expected to upload directly to object storage and return URL
        "upload_to_storage": True,
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{settings.blender_server_url.rstrip('/')}/render-asset",
                json=payload,
            )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"status": "error", "error": f"Blender MCP render error: {exc}"}


def render_related_anatomy(question: str, answer: str = "", sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Best-effort anatomy asset render for RAG.
    Returns only remote URL metadata; backend does not persist local render files.
    """
    key = _extract_anatomy_key(question, answer=answer, sources=sources)
    if not key:
        return {"status": "skipped", "reason": "No mapped anatomy keyword found."}

    mapping = ASSET_MAPPING.get(key)
    if not mapping:
        return {"status": "skipped", "reason": f"No asset mapping configured for '{key}'."}

    render = _call_remote_asset_render(
        asset_key=mapping["asset_key"],
        camera_preset=mapping["camera_preset"],
        request_id=f"rag_{key}",
    )
    if render.get("status") not in {"ok", "generated", "rendered"}:
        return {
            "status": "error",
            "anatomy_key": key,
            "error": render.get("error", "Remote render failed."),
        }

    # allow different worker payload shapes
    render_url = (
        render.get("render_url")
        or render.get("preview_url")
        or render.get("image_url")
        or render.get("url")
    )
    if not render_url:
        return {
            "status": "error",
            "anatomy_key": key,
            "error": "Remote render succeeded but returned no URL.",
        }

    return {
        "status": "rendered",
        "anatomy_key": key,
        "render_3d_url": render_url,
        "render_3d_model_url": render.get("model_url"),
        "camera_preset": mapping["camera_preset"],
        "asset_key": mapping["asset_key"],
    }
