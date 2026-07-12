import mimetypes
import re
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


def _match_anatomy_key_in_text(text: str) -> Optional[str]:
    """
    Return the first anatomy key whose synonym appears in `text` as a whole word.

    Word-boundary matching (\\b) avoids substring false positives such as
    "cerebral" matching inside unrelated words, and prefers longer/more-specific
    synonyms first so e.g. "vertebrae" wins over a stray "spinal".
    """
    lowered = (text or "").lower()
    if not lowered.strip():
        return None
    # Longer tokens first: more specific terms take priority over generic ones.
    for token, key in sorted(ANATOMY_SYNONYMS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            return key
    return None


def _extract_anatomy_key(question: str, answer: str = "", sources: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Resolve one anatomy key for the legacy asset renderer.

    Only the user's question is considered first; the generated answer is a weak
    fallback used *only* when the question itself contains no anatomy term.

    Retrieved source text (`sources`) is intentionally IGNORED: index/glossary/TOC
    chunks routinely contain incidental anatomy words (e.g. "cerebral", "hand"),
    which previously caused the wrong 3D model to be attached to unrelated answers
    (e.g. "brain" for a hip-flexor question). `sources` is kept in the signature
    for backward compatibility only.
    """
    return _match_anatomy_key_in_text(question) or _match_anatomy_key_in_text(answer)


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


# Minimum confidence to auto-export via MCP during RAG enrichment (below chat auto-export threshold).
MCP_RAG_EXPORT_CONFIDENCE = 0.85


def _combined_anatomy_text(
    question: str,
    answer: str = "",
    sources: Optional[List[Dict[str, Any]]] = None,
) -> str:
    source_text = ""
    if sources:
        source_text = " ".join((s.get("chunk_preview") or "") for s in sources if isinstance(s, dict))
    return f"{question}\n{answer}\n{source_text}".strip()


def _try_mcp_catalog_render(
    question: str,
    answer: str = "",
    sources: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Resolve an exportable Z-Anatomy part via MCP catalog suggestions, then export preview.
    """
    try:
        from anatomy_mcp.query_validation import catalog_query_from_user_message, is_vague_part_query
        from app.services.anatomy_mcp_service import export_anatomy_part, suggest_exportable_anatomy
    except Exception as exc:
        return {"status": "skipped", "reason": f"MCP anatomy modules unavailable: {exc}"}

    catalog_query = catalog_query_from_user_message(question)
    if not catalog_query or is_vague_part_query(catalog_query):
        for text in (answer, _combined_anatomy_text("", answer, sources)):
            if not text:
                continue
            candidate = catalog_query_from_user_message(text)
            if candidate and not is_vague_part_query(candidate):
                catalog_query = candidate
                break

    if not catalog_query or is_vague_part_query(catalog_query):
        return {"status": "skipped", "reason": "No specific anatomy query for MCP catalog."}

    suggest = suggest_exportable_anatomy(catalog_query, limit=6, include_nearby=True)
    if suggest.get("error"):
        return {"status": "skipped", "reason": str(suggest.get("error"))}

    suggestions = suggest.get("suggestions") or []
    suggestion_labels = [
        str(row.get("label"))
        for row in suggestions
        if isinstance(row, dict) and row.get("label") and row.get("can_export")
    ]

    candidate = suggest.get("auto_export_candidate")
    if not candidate and suggestions:
        top = suggestions[0]
        if isinstance(top, dict) and float(top.get("confidence") or 0) >= MCP_RAG_EXPORT_CONFIDENCE:
            candidate = top

    if not candidate or not candidate.get("label"):
        return {
            "status": "skipped",
            "reason": "No high-confidence exportable catalog match.",
            "render_3d_suggestions": suggestion_labels[:6],
        }

    export = export_anatomy_part(part_query=str(candidate["label"]), include_preview=True)
    if export.get("error"):
        return {
            "status": "skipped",
            "reason": str(export.get("error")),
            "render_3d_suggestions": suggestion_labels[:6],
        }

    preview_url = export.get("preview_url")
    model_url = export.get("model_url")
    annotations_url = export.get("annotations_url")
    viewer_url = export.get("viewer_url")
    render_url = preview_url or model_url
    if not render_url:
        return {
            "status": "skipped",
            "reason": "MCP export succeeded but returned no preview/model URL.",
            "render_3d_suggestions": suggestion_labels[:6],
        }

    return {
        "status": "rendered",
        "anatomy_key": candidate.get("label"),
        "render_3d_url": render_url,
        "render_3d_model_url": model_url,
        "render_3d_viewer_url": viewer_url,
        "render_3d_annotations_url": annotations_url,
        "render_source": "mcp_exportable_catalog",
        "match_reason": candidate.get("match_reason"),
        "confidence": candidate.get("confidence"),
        "render_3d_suggestions": suggestion_labels[:6],
    }


def _legacy_asset_render(
    question: str,
    answer: str = "",
    sources: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
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
        "render_source": "legacy_blend_asset",
    }


def render_related_anatomy(question: str, answer: str = "", sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Best-effort anatomy asset render for RAG.
    Prefers MCP exportable_catalog export; falls back to legacy preloaded .blend assets.
    """
    mcp_result = _try_mcp_catalog_render(question, answer=answer, sources=sources)
    if mcp_result.get("status") == "rendered":
        return mcp_result

    legacy_result = _legacy_asset_render(question, answer=answer, sources=sources)
    suggestions = mcp_result.get("render_3d_suggestions") or []
    if legacy_result.get("status") == "rendered":
        if suggestions and not legacy_result.get("render_3d_suggestions"):
            legacy_result["render_3d_suggestions"] = suggestions
        return legacy_result

    # Neither path produced a real render. Do NOT surface a speculative
    # `anatomy_key`: it would set `render_3d_anatomy` in the API response and make
    # the UI show a 3D label with no actual model/preview behind it.
    return {
        "status": "skipped",
        "render_3d_suggestions": suggestions,
    }
