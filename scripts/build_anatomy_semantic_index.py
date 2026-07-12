"""Build the MiniLM semantic fallback index for the exportable Z-Anatomy catalog.

Run once after ``build_exportable_catalog.py`` produces
``anatomy_mcp/label_index/exportable_catalog.json``. No Blender required — this
only reads the catalog JSON and embeds each entry's description.

Usage (from repo root, inside the venv):

    python scripts/build_anatomy_semantic_index.py
"""

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from anatomy_mcp.semantic_index import build_semantic_index


def main() -> int:
    summary = build_semantic_index()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
