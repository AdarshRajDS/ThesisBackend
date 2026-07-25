"""Write a portable full Anatomy Viewer package (same UI/controls as /anatomy-viewer).

Creates:
  exports/shareable/{slug}/index.html   — full viewer (relative assets)
  exports/shareable/{slug}.zip          — zip to email the professor
  exports/shareable/{slug}.html         — single-file portable copy (CDN Three.js + embedded GLB)

The single-file HTML embeds the model/annotations and uses the real viewer.js
(with CDN import paths), so behaviour matches the live Anatomy Viewer.
"""

from __future__ import annotations

import base64
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

try:
    from config import EXPORT_ROOT, VIEWER_DIR
except ImportError:
    from anatomy_mcp.config import EXPORT_ROOT, VIEWER_DIR

SHAREABLE_DIR = EXPORT_ROOT / "shareable"
HTML_DIR = EXPORT_ROOT / "html"

_MAX_EMBED_BYTES = 18 * 1024 * 1024
_THREE_CDN = "https://cdn.jsdelivr.net/npm/three@0.170.0"

_VENDOR_FILES = [
    "build/three.module.js",
    "examples/jsm/controls/OrbitControls.js",
    "examples/jsm/loaders/GLTFLoader.js",
    "examples/jsm/postprocessing/EffectComposer.js",
    "examples/jsm/postprocessing/RenderPass.js",
    "examples/jsm/postprocessing/GTAOPass.js",
    "examples/jsm/postprocessing/OutputPass.js",
    "examples/jsm/postprocessing/Pass.js",
    "examples/jsm/postprocessing/ShaderPass.js",
    "examples/jsm/postprocessing/MaskPass.js",
    "examples/jsm/shaders/CopyShader.js",
    "examples/jsm/shaders/OutputShader.js",
    "examples/jsm/shaders/GTAOShader.js",
    "examples/jsm/shaders/PoissonDenoiseShader.js",
    "examples/jsm/math/SimplexNoise.js",
    "examples/jsm/utils/BufferGeometryUtils.js",
]


def slugify_part_label(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return slug or "anatomy_part"


def export_public_path(file_path: Path) -> str:
    rel = file_path.resolve().relative_to(EXPORT_ROOT.resolve()).as_posix()
    return f"/anatomy-exports/{rel}"


def _portable_viewer_js(source: str) -> str:
    """Rewrite local vendor imports to CDN three/addons paths."""
    repl = [
        (
            'from "./vendor/three/examples/jsm/controls/OrbitControls.js"',
            'from "three/addons/controls/OrbitControls.js"',
        ),
        (
            'from "./vendor/three/examples/jsm/loaders/GLTFLoader.js"',
            'from "three/addons/loaders/GLTFLoader.js"',
        ),
        (
            'from "./vendor/three/examples/jsm/postprocessing/EffectComposer.js"',
            'from "three/addons/postprocessing/EffectComposer.js"',
        ),
        (
            'from "./vendor/three/examples/jsm/postprocessing/RenderPass.js"',
            'from "three/addons/postprocessing/RenderPass.js"',
        ),
        (
            'from "./vendor/three/examples/jsm/postprocessing/GTAOPass.js"',
            'from "three/addons/postprocessing/GTAOPass.js"',
        ),
        (
            'from "./vendor/three/examples/jsm/postprocessing/OutputPass.js"',
            'from "three/addons/postprocessing/OutputPass.js"',
        ),
    ]
    out = source
    for old, new in repl:
        out = out.replace(old, new)
    # Defaults unused when ANATOMY_* is set; keep harmless relative fallbacks.
    out = out.replace(
        'const fallbackModel     = "../exports/glb/liver_test.glb";',
        'const fallbackModel     = "./model.glb";',
    )
    out = out.replace(
        'const fallbackAnno      = "../exports/annotations/liver_test.annotations.json";',
        'const fallbackAnno      = "./annotations.json";',
    )
    return out


def _copy_vendor(dest_vendor: Path) -> None:
    src_root = VIEWER_DIR / "vendor" / "three"
    for rel in _VENDOR_FILES:
        src = src_root / rel
        if not src.exists():
            continue
        dst = dest_vendor / "three" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _write_package_index(
    pkg: Path,
    part_label: str,
    *,
    use_cdn: bool,
    filename: str = "index.html",
) -> None:
    title = html.escape(part_label)
    title_js = html.escape(part_label, quote=True)
    if use_cdn:
        importmap = f"""    <script type="importmap">
      {{
        "imports": {{
          "three": "{_THREE_CDN}/build/three.module.js",
          "three/addons/": "{_THREE_CDN}/examples/jsm/"
        }}
      }}
    </script>"""
        viewer_src = "./viewer.cdn.js"
    else:
        importmap = """    <script type="importmap">
      {
        "imports": {
          "three": "./vendor/three/build/three.module.js"
        }
      }
    </script>"""
        viewer_src = "./viewer.js"

    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} — Anatomy Viewer</title>
    <link rel="stylesheet" href="./styles.css">
{importmap}
    <script>
      window.ANATOMY_MODEL = "./model.glb";
      window.ANATOMY_ANNOTATIONS = "./annotations.json";
      window.ANATOMY_TITLE = "{title_js}";
    </script>
  </head>
  <body>
    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar__header">
          <p class="eyebrow">Anatomy Viewer</p>
          <h1 id="part-title">{title}</h1>
          <p class="sidebar__copy">Clean GLB geometry with annotation labels driven by structured JSON.</p>
        </div>
        <div class="sidebar__controls">
          <label class="toggle">
            <input id="labels-toggle" type="checkbox" checked>
            <span>Show labels</span>
          </label>
        </div>
        <ol id="annotation-list" class="annotation-list"></ol>
      </aside>
      <main class="viewer-stage">
        <div id="viewer-canvas"></div>
        <div id="labels-layer" class="labels-layer"></div>
      </main>
    </div>

    <script type="module" src="{viewer_src}"></script>
  </body>
</html>
"""
    (pkg / filename).write_text(page, encoding="utf-8")


def _write_single_file_html(
    *,
    part_label: str,
    glb_b64: str,
    annotations_obj: dict[str, Any],
    styles_css: str,
    viewer_cdn_js: str,
) -> str:
    """One emailable HTML file: full viewer.js + embedded GLB/annotations + CDN Three."""
    title = html.escape(part_label)
    title_js = json.dumps(part_label)
    anno_json = json.dumps(annotations_obj, ensure_ascii=False)
    styles_json = json.dumps(styles_css)
    glb_json = json.dumps(glb_b64)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Anatomy Viewer</title>
  <script type="importmap">
  {{
    "imports": {{
      "three": "{_THREE_CDN}/build/three.module.js",
      "three/addons/": "{_THREE_CDN}/examples/jsm/"
    }}
  }}
  </script>
  <script>
    (function () {{
      const css = {styles_json};
      const style = document.createElement("style");
      style.textContent = css;
      document.head.appendChild(style);
    }})();
  </script>
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar__header">
        <p class="eyebrow">Anatomy Viewer</p>
        <h1 id="part-title">{title}</h1>
        <p class="sidebar__copy">Clean GLB geometry with annotation labels driven by structured JSON.</p>
      </div>
      <div class="sidebar__controls">
        <label class="toggle">
          <input id="labels-toggle" type="checkbox" checked>
          <span>Show labels</span>
        </label>
      </div>
      <ol id="annotation-list" class="annotation-list"></ol>
    </aside>
    <main class="viewer-stage">
      <div id="viewer-canvas"></div>
      <div id="labels-layer" class="labels-layer"></div>
    </main>
  </div>

  <script type="module">
    function b64ToBytes(b64) {{
      const bin = atob(b64);
      const out = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return out;
    }}
    const glbBytes = b64ToBytes({glb_json});
    const annoText = {json.dumps(anno_json)};
    window.ANATOMY_MODEL = URL.createObjectURL(new Blob([glbBytes], {{ type: "model/gltf-binary" }}));
    window.ANATOMY_ANNOTATIONS = URL.createObjectURL(
      new Blob([annoText], {{ type: "application/json" }})
    );
    window.ANATOMY_TITLE = {title_js};
  </script>
  <script type="module">
{viewer_cdn_js}
  </script>
</body>
</html>
"""


def write_export_html_page(
    *,
    part_label: str,
    model_path: Path,
    annotations_path: Path,
) -> dict[str, Any]:
    SHAREABLE_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    slug = slugify_part_label(part_label)
    pkg = SHAREABLE_DIR / slug
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    # Assets
    shutil.copy2(model_path, pkg / "model.glb")
    shutil.copy2(annotations_path, pkg / "annotations.json")
    shutil.copy2(VIEWER_DIR / "styles.css", pkg / "styles.css")

    viewer_src = (VIEWER_DIR / "viewer.js").read_text(encoding="utf-8")
    (pkg / "viewer.js").write_text(viewer_src, encoding="utf-8")
    viewer_cdn = _portable_viewer_js(viewer_src)
    (pkg / "viewer.cdn.js").write_text(viewer_cdn, encoding="utf-8")
    _copy_vendor(pkg / "vendor")

    # Full offline package (identical to live /anatomy-viewer).
    _write_package_index(pkg, part_label, use_cdn=False, filename="index.html")
    _write_package_index(pkg, part_label, use_cdn=True, filename="index.cdn.html")

    (pkg / "README.txt").write_text(
        f"""{part_label} — portable Anatomy Viewer
=====================================

This folder is a full copy of the thesis Anatomy Viewer for this export
(same labels, views, cross-section, exploded view, materials).

How to open
-----------
1. Double-click open.bat   (Windows), OR
2. In this folder run:  python -m http.server 5500
   then open http://127.0.0.1:5500/

Do not rely on the thesis backend / localhost:8000 — this package is self-contained.

Files
-----
index.html       full viewer
model.glb        3D model
annotations.json labels
viewer.js / vendor/   viewer runtime
""",
        encoding="utf-8",
    )
    (pkg / "open.bat").write_text(
        "@echo off\n"
        "cd /d \"%~dp0\"\n"
        "echo Starting local viewer at http://127.0.0.1:5500/\n"
        "echo Press Ctrl+C to stop.\n"
        "start \"\" http://127.0.0.1:5500/\n"
        "python -m http.server 5500\n"
        "pause\n",
        encoding="utf-8",
    )

    # Zip for email
    zip_path = SHAREABLE_DIR / f"{slug}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in pkg.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=f"{slug}/{path.relative_to(pkg).as_posix()}")

    # Single-file HTML (full viewer + embedded model) for quick sharing.
    glb_bytes = model_path.read_bytes()
    single_path = SHAREABLE_DIR / f"{slug}.html"
    if len(glb_bytes) <= _MAX_EMBED_BYTES:
        annotations_obj = json.loads(annotations_path.read_text(encoding="utf-8"))
        if not isinstance(annotations_obj, dict):
            annotations_obj = {"part_label": part_label, "annotations": []}
        annotations_obj.setdefault("part_label", part_label)
        styles_css = (VIEWER_DIR / "styles.css").read_text(encoding="utf-8")
        single_html = _write_single_file_html(
            part_label=part_label,
            glb_b64=base64.b64encode(glb_bytes).decode("ascii"),
            annotations_obj=annotations_obj,
            styles_css=styles_css,
            viewer_cdn_js=viewer_cdn,
        )
        single_path.write_text(single_html, encoding="utf-8")
        (HTML_DIR / f"{slug}.html").write_text(single_html, encoding="utf-8")
    else:
        # Too large to embed — point people at the zip/folder.
        single_path.write_text(
            f"""<!doctype html><meta charset="utf-8">
<title>{html.escape(part_label)}</title>
<p>Model is too large for a single HTML embed. Use the folder package
<code>{html.escape(str(pkg))}</code> or zip <code>{html.escape(zip_path.name)}</code>
and run <code>open.bat</code>.</p>""",
            encoding="utf-8",
        )

    return {
        "html_path": str(single_path.resolve()),
        "html_package_dir": str(pkg.resolve()),
        "html_zip_path": str(zip_path.resolve()),
        "html_url": export_public_path(single_path),
        "html_zip_url": export_public_path(zip_path),
        "html_package_url": export_public_path(pkg / "index.html"),
        "html_slug": slug,
        "html_bytes": single_path.stat().st_size if single_path.exists() else 0,
        "portable": True,
    }


def attach_html_page_to_response(
    response: dict[str, Any],
    *,
    model_path: Path | None,
    annotations_path: Path | None,
) -> dict[str, Any]:
    if not isinstance(response, dict):
        return response
    label = str(response.get("part_label") or "anatomy")
    if not model_path or not annotations_path:
        return response
    if not model_path.exists() or not annotations_path.exists():
        return response
    try:
        meta = write_export_html_page(
            part_label=label,
            model_path=model_path,
            annotations_path=annotations_path,
        )
        response["html_url"] = meta["html_url"]
        response["html_path"] = meta["html_path"]
        response["html_zip_url"] = meta.get("html_zip_url")
        response["html_zip_path"] = meta.get("html_zip_path")
        response["html_package_dir"] = meta.get("html_package_dir")
        response["html_portable"] = True
    except Exception as exc:
        response["html_error"] = str(exc)
    return response
