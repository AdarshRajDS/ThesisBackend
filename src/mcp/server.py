from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os
import subprocess
import tempfile
import uuid

from src.mcp.blender_mcp import BlenderMCP
from app.services.object_storage import get_presigned_url, put_object

app = FastAPI(title="Blender MCP Server")

mcp = BlenderMCP()

ASSET_FILE_ALIASES = {
    # Prefer a stable clean file when available for headless rendering.
    "brain": ["brain_clean.blend", "brain.blend"],
    "heart": ["heart.blend"],
    "hand": ["hand.blend"],
    "lung": ["lung.blend"],
    "spine": ["spine.blend"],
}


class GenerateRequest(BaseModel):
    prompt: str
    quality: str = "standard"
    format: str = "glb"
    include_preview: bool = True


class GenerateResponse(BaseModel):
    status: str
    task_id: Optional[str] = None
    model_path: Optional[str] = None
    preview_path: Optional[str] = None
    error: Optional[str] = None


class RenderAssetRequest(BaseModel):
    asset_key: str
    camera_preset: str = "frontal-superior"
    request_id: Optional[str] = None
    output_format: str = "png"
    upload_to_storage: bool = True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    result = mcp.generate_3d_brain(
        request.prompt,
        request.quality,
        request.format,
        request.include_preview,
    )

    if result.get("status") != "generated":
        raise HTTPException(status_code=500, detail=result.get("error", "Blender generation failed."))

    return {
        "status": "generated",
        "task_id": result.get("task_id"),
        "model_path": result.get("model_path"),
        "preview_path": result.get("preview_path"),
    }


def _assets_dir() -> Path:
    return Path(os.getenv("BLENDER_ASSETS_DIR", "/code/assets"))


def _resolve_asset_path(asset_key: str) -> Path:
    base = _assets_dir()
    candidates = ASSET_FILE_ALIASES.get(asset_key, [f"{asset_key}.blend"])
    for name in candidates:
        p = base / name
        if p.exists():
            return p
    # fallback for diagnostics
    return base / f"{asset_key}.blend"


@app.post("/render-asset")
def render_asset(request: RenderAssetRequest):
    asset_path = _resolve_asset_path(request.asset_key)
    if not asset_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "error": f"Asset not found: {asset_path}",
                "hint": "Mount preloaded .blend files under BLENDER_ASSETS_DIR (default /code/assets).",
            },
        )

    renderer_script = Path(__file__).resolve().parent / "blender_asset_renderer.py"
    if not renderer_script.exists():
        raise HTTPException(status_code=500, detail="Renderer script missing.")

    rid = request.request_id or f"{request.asset_key}_{uuid.uuid4().hex[:10]}"
    render_timeout = int(os.getenv("BLENDER_RENDER_TIMEOUT_SECONDS", "900"))
    enable_autoexec = os.getenv("BLENDER_ENABLE_AUTOEXEC", "false").lower() in ("1", "true", "yes")
    with tempfile.TemporaryDirectory(prefix="blend_render_") as td:
        output_path = Path(td) / f"{rid}.png"
        model_path = Path(td) / f"{rid}.glb"
        cmd = [
            "blender",
            "--background",
            "--factory-startup",
        ]
        if enable_autoexec:
            cmd.append("--enable-autoexec")
        cmd += [
            "--python",
            str(renderer_script),
            "--",
            "--asset",
            str(asset_path),
            "--camera-preset",
            request.camera_preset,
            "--output",
            str(output_path),
            "--output-model",
            str(model_path),
        ]
        try:
            done = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=render_timeout,
                cwd="/code",
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail=f"Render timed out: {exc}") from exc

        if done.returncode != 0:
            # Some template/startup scripts can fail in headless mode while render still succeeds.
            if output_path.exists() and output_path.stat().st_size > 0:
                pass
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "status": "error",
                        "error": "Blender render failed.",
                        "asset_path": str(asset_path),
                        "stdout": done.stdout[-3000:],
                        "stderr": done.stderr[-3000:],
                    },
                )

        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "error": "Blender did not produce output PNG.",
                    "asset_path": str(asset_path),
                    "stdout": done.stdout[-3000:],
                    "stderr": done.stderr[-3000:],
                },
            )

        # Upload directly to object storage; backend should not persist local files.
        image_key = f"blender/renders/{request.asset_key}/{rid}.png"
        image_bytes = output_path.read_bytes()
        ok_image = put_object(image_key, image_bytes, content_type="image/png")
        if not ok_image:
            raise HTTPException(status_code=500, detail="Rendered image upload failed.")

        model_url = None
        model_key = None
        if model_path.exists() and model_path.stat().st_size > 0:
            model_key = f"blender/models/{request.asset_key}/{rid}.glb"
            model_bytes = model_path.read_bytes()
            ok_model = put_object(model_key, model_bytes, content_type="model/gltf-binary")
            if ok_model:
                model_url = get_presigned_url(model_key)

    render_url = get_presigned_url(image_key)
    if not render_url:
        raise HTTPException(status_code=500, detail="Upload succeeded but URL generation failed.")

    return {
        "status": "ok",
        "asset_key": request.asset_key,
        "asset_path": str(asset_path),
        "camera_preset": request.camera_preset,
        "storage_key": image_key,
        "render_url": render_url,
        "model_storage_key": model_key,
        "model_url": model_url,
    }
