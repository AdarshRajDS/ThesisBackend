import os
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = Path(os.getenv("ANATOMY_MCP_ROOT", str(THIS_DIR)))

BLENDER_EXE = Path(
    os.getenv(
        "BLENDER_BIN",
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    )
)

Z_ANATOMY_BLEND = Path(
    os.getenv(
        "Z_ANATOMY_BLEND",
        r"C:\Users\Admin\Downloads\Z-Anatomy (1)\Z-Anatomy\Startup.blend",
    )
)

LABEL_INDEX_PATH = PROJECT_ROOT / "label_index" / "z_anatomy_index.json"
EXPORTABLE_CATALOG_PATH = PROJECT_ROOT / "label_index" / "exportable_catalog.json"

EXPORT_ROOT = PROJECT_ROOT / "exports"
GLB_DIR = EXPORT_ROOT / "glb"
PREVIEW_DIR = EXPORT_ROOT / "preview"
ANNOTATIONS_DIR = EXPORT_ROOT / "annotations"
SCENE_SCAN_DIR = EXPORT_ROOT / "scene_scan"
MANIFESTS_DIR = EXPORT_ROOT / "manifests"
PACKAGES_DIR = EXPORT_ROOT / "packages"
CACHE_DIR = EXPORT_ROOT / "cache"
CACHE_GLB_DIR = CACHE_DIR / "glb"
CACHE_ANNOTATIONS_DIR = CACHE_DIR / "annotations"
CACHE_PREVIEW_DIR = CACHE_DIR / "preview"
CACHE_PACKAGES_DIR = CACHE_DIR / "packages"
CACHE_SCHEMA_VERSION = "v4"

BLENDER_SCRIPTS_DIR = PROJECT_ROOT / "blender_scripts"
SCAN_SCRIPT = BLENDER_SCRIPTS_DIR / "scan_z_anatomy.py"
BUILD_EXPORTABLE_CATALOG_SCRIPT = BLENDER_SCRIPTS_DIR / "build_exportable_catalog.py"
SCAN_SCENE_FULL_SCRIPT = BLENDER_SCRIPTS_DIR / "scan_scene_full.py"
SCAN_ANNOTATIONS_FULL_SCRIPT = BLENDER_SCRIPTS_DIR / "scan_annotations_full.py"
EXPORT_SCRIPT = BLENDER_SCRIPTS_DIR / "export_part.py"
EXPORT_STUDY_PACKAGE_SCRIPT = BLENDER_SCRIPTS_DIR / "export_study_package.py"
VIEWER_DIR = PROJECT_ROOT / "viewer"

LOGS_DIR = PROJECT_ROOT / "logs"
EXPORT_LOG_PATH = LOGS_DIR / "exports.log"

PUBLIC_BASE_URL = os.getenv(
    "ANATOMY_MCP_PUBLIC_BASE_URL",
    "http://127.0.0.1:8000/anatomy-exports",
)
PUBLIC_VIEWER_URL = os.getenv(
    "ANATOMY_MCP_VIEWER_URL",
    "http://127.0.0.1:8000/anatomy-viewer/index.html",
)

MAX_QUERY_LENGTH = 80

BLENDER_EXPORT_TIMEOUT_SECONDS = int(os.getenv("BLENDER_EXPORT_TIMEOUT_SECONDS", "300"))
BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS = int(
    os.getenv("BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS", "900")
)
