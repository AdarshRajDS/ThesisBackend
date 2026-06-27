"""Bridge to the true stdio MCP server in ``anatomy_mcp/server.py``."""

from __future__ import annotations

import importlib
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from src.config.settings import settings

_ANATOMY_MCP_ROOT = Path(__file__).resolve().parents[2] / "anatomy_mcp"


def configure_anatomy_mcp_urls(public_api_base: Optional[str] = None) -> None:
    """Set public URLs before importing anatomy MCP modules."""
    base = (public_api_base or settings.public_api_base or "http://127.0.0.1:8000").rstrip("/")
    os.environ["ANATOMY_MCP_ROOT"] = str(_ANATOMY_MCP_ROOT)
    os.environ["ANATOMY_MCP_PUBLIC_BASE_URL"] = f"{base}/anatomy-exports"
    os.environ["ANATOMY_MCP_VIEWER_URL"] = f"{base}/anatomy-viewer/index.html"
    if settings.blender_bin:
        os.environ["BLENDER_BIN"] = settings.blender_bin
    if settings.z_anatomy_blend:
        os.environ["Z_ANATOMY_BLEND"] = settings.z_anatomy_blend


def _ensure_pywin32() -> None:
    """Make pywin32 DLLs discoverable on Windows (required by mcp stdio client)."""
    if sys.platform != "win32":
        return
    try:
        import pywintypes  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    candidates = []
    for entry in sys.path:
        if entry:
            candidates.append(Path(entry) / "pywin32_system32")

    venv_root = Path(sys.executable).resolve().parent.parent
    candidates.append(venv_root / "Lib" / "site-packages" / "pywin32_system32")

    for dll_dir in candidates:
        if not dll_dir.is_dir():
            continue
        dll_path = str(dll_dir)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(dll_path)
        os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")

    import pywintypes  # noqa: F401


# Prepare pywin32 DLL path before any ``mcp`` import (Windows stdio client).
try:
    _ensure_pywin32()
except ModuleNotFoundError:
    pass


def _ensure_import_path() -> None:
    root = str(_ANATOMY_MCP_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


@lru_cache(maxsize=1)
def _server_module():
    configure_anatomy_mcp_urls()
    _ensure_pywin32()
    _ensure_import_path()
    import config as anatomy_config  # noqa: WPS433

    importlib.reload(anatomy_config)
    import server as anatomy_server  # noqa: WPS433

    importlib.reload(anatomy_server)
    return anatomy_server


def anatomy_mcp_health() -> dict[str, Any]:
    configure_anatomy_mcp_urls()
    _ensure_pywin32()
    _ensure_import_path()
    import config as anatomy_config  # noqa: WPS433

    mcp_import_ok = True
    mcp_import_error = None
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except Exception as exc:
        mcp_import_ok = False
        mcp_import_error = str(exc)

    checks = {
        "anatomy_mcp_root": str(_ANATOMY_MCP_ROOT),
        "blender_exe": str(anatomy_config.BLENDER_EXE),
        "blender_exists": anatomy_config.BLENDER_EXE.exists(),
        "z_anatomy_blend": str(anatomy_config.Z_ANATOMY_BLEND),
        "z_anatomy_exists": anatomy_config.Z_ANATOMY_BLEND.exists(),
        "label_index": str(anatomy_config.LABEL_INDEX_PATH),
        "label_index_exists": anatomy_config.LABEL_INDEX_PATH.exists(),
        "exportable_catalog": str(anatomy_config.EXPORTABLE_CATALOG_PATH),
        "exportable_catalog_exists": anatomy_config.EXPORTABLE_CATALOG_PATH.exists(),
        "public_base_url": anatomy_config.PUBLIC_BASE_URL,
        "viewer_url": anatomy_config.PUBLIC_VIEWER_URL,
        "mcp_import_ok": mcp_import_ok,
        "mcp_import_error": mcp_import_error,
    }
    ready = (
        checks["blender_exists"]
        and checks["z_anatomy_exists"]
        and checks["label_index_exists"]
        and mcp_import_ok
    )
    return {
        "status": "ok" if ready else "degraded",
        "ready": ready,
        "checks": checks,
    }


def search_anatomy_catalog(query: str, limit: int = 10) -> dict[str, Any]:
    server = _server_module()
    return server.search_anatomy_catalog(query=query, limit=limit)


def export_anatomy_part(
    part_query: str,
    include_preview: bool = True,
    region_hint: Optional[str] = None,
) -> dict[str, Any]:
    server = _server_module()
    return server.export_anatomy_part(
        part_query=part_query,
        include_preview=include_preview,
        region_hint=region_hint,
    )
