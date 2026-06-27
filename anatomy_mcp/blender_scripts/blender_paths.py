"""Paths for Blender background scripts (writes under anatomy_mcp/, not blendermcp)."""

from __future__ import annotations

import os
from pathlib import Path

# anatomy_mcp/ (parent of blender_scripts/)
ANATOMY_MCP_ROOT = Path(
    os.getenv("ANATOMY_MCP_ROOT", str(Path(__file__).resolve().parents[1]))
).resolve()

LABEL_INDEX_DIR = ANATOMY_MCP_ROOT / "label_index"
EXPORTABLE_CATALOG_PATH = LABEL_INDEX_DIR / "exportable_catalog.json"
Z_ANATOMY_INDEX_PATH = LABEL_INDEX_DIR / "z_anatomy_index.json"
EXPORT_ROOT = ANATOMY_MCP_ROOT / "exports"
SCENE_SCAN_DIR = EXPORT_ROOT / "scene_scan"
