"""LLM configuration and LM Studio reachability checks."""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from src.config.settings import settings
from src.llm.llm_factory import _assert_local_api_base, llm_config_snapshot

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/llm")
async def debug_llm():
    """
    Verify local-only LLM configuration and whether LM Studio responds on /v1/models.
    """
    snapshot = llm_config_snapshot()
    out: dict[str, object] = {
        **snapshot,
        "legacy_groq_env_ignored": bool(__import__("os").getenv("GROQ_API_KEY")),
        "local_endpoint_ok": True,
        "local_endpoint_error": None,
        "lmstudio_reachable": False,
        "lmstudio_models": None,
        "lmstudio_error": None,
    }

    try:
        _assert_local_api_base(settings.llm_api_base)
    except RuntimeError as exc:
        out["local_endpoint_ok"] = False
        out["local_endpoint_error"] = str(exc)
        return out

    models_url = settings.llm_api_base.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                models_url,
                headers={"Authorization": f"Bearer {settings.llm_api_key or 'lm-studio'}"},
            )
        if resp.status_code == 200:
            payload = resp.json()
            out["lmstudio_reachable"] = True
            data = payload.get("data") if isinstance(payload, dict) else None
            if isinstance(data, list):
                out["lmstudio_models"] = [
                    m.get("id") for m in data if isinstance(m, dict) and m.get("id")
                ][:20]
        else:
            out["lmstudio_error"] = f"HTTP {resp.status_code} from {models_url}"
    except Exception as exc:
        out["lmstudio_error"] = str(exc)

    return out
