#!/usr/bin/env python3
"""Export professor Blender test structures and build a static GitHub Pages gallery."""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000"
OUT = REPO / "docs" / "professor-blender-demo"
MODELS = OUT / "models"
ANNOS = OUT / "annotations"
VIEWER_SRC = REPO / "anatomy_mcp" / "viewer"
EXPORTS = REPO / "anatomy_mcp" / "exports"

# German label -> preferred Z-Anatomy catalog label
STRUCTURES = [
    {"de": "Leber", "en": "Liver", "label": "Liver", "slug": "leber"},
    {"de": "Pankreas", "en": "Pancreas", "label": "Pancreas", "slug": "pankreas"},
    {
        "de": "Nebenniere",
        "en": "Suprarenal gland (left)",
        "label": "Suprarenal gland.l",
        "slug": "nebenniere",
    },
    {
        "de": "Nervus facialis",
        "en": "Facial nerve (VII)",
        "label": "Facial nerve (VII)",
        "slug": "nervus-facialis",
    },
    {
        "de": "Auge und visuelles System",
        "en": "Accessory visual structures",
        "label": "Accessory visual structures",
        "slug": "auge-visuelles-system",
    },
    {"de": "Incus", "en": "Incus (left)", "label": "Incus.l", "slug": "incus"},
    {
        "de": "Linea aspera",
        "en": "Linea aspera",
        "label": "Linea aspera.i",
        "slug": "linea-aspera",
    },
    {
        "de": "Trochanter major",
        "en": "Greater trochanter",
        "label": "Greater trochanter.i",
        "slug": "trochanter-major",
    },
    {
        "de": "Musculus quadriceps femoris",
        "en": "Quadriceps femoris muscle",
        "label": "Quadriceps femoris muscle.el",
        "slug": "m-quadriceps-femoris",
    },
    {"de": "Kniegelenk", "en": "Knee joint", "label": "Knee joint", "slug": "kniegelenk"},
    {
        "de": "Sprunggelenk",
        "en": "Ankle joint",
        "label": "Ankle joint",
        "slug": "sprunggelenk",
    },
]


def slugify(label: str) -> str:
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "part"


def post_json(path: str, payload: dict, timeout: int = 360) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def local_from_url(url: str | None) -> Path | None:
    if not url:
        return None
    # e.g. http://127.0.0.1:8000/anatomy-exports/glb/liver_xxx.glb
    marker = "/anatomy-exports/"
    if marker not in url:
        return None
    rel = url.split(marker, 1)[1].split("?", 1)[0]
    path = EXPORTS / Path(rel)
    return path if path.exists() else None


def copy_asset(src: Path | None, dest: Path) -> bool:
    if not src or not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def export_one(item: dict, *, force: bool = False) -> dict:
    slug = item["slug"]
    glb_dest = MODELS / f"{slug}.glb"
    anno_dest = ANNOS / f"{slug}.annotations.json"
    if (
        not force
        and glb_dest.exists()
        and glb_dest.stat().st_size >= 1024
        and anno_dest.exists()
    ):
        size_mb = round(glb_dest.stat().st_size / (1024 * 1024), 3)
        print(f"\n=== Skip existing {item['de']} ({size_mb} MB) ===", flush=True)
        return {
            **item,
            "status": "ok",
            "error": None,
            "part_label": item["label"],
            "model_file": f"models/{slug}.glb",
            "annotations_file": f"annotations/{slug}.annotations.json",
            "size_mb": size_mb,
            "elapsed_s": 0,
            "cache_hit": True,
            "viewer_query": (
                f"viewer.html?model=models/{slug}.glb"
                f"&annotations=annotations/{slug}.annotations.json"
                f"&title={urllib.parse.quote(item['de'])}"
            ),
        }

    label = item["label"]
    print(f"\n=== Exporting {item['de']} -> {label!r} ===", flush=True)
    t0 = time.time()
    try:
        result = post_json(
            "/anatomy/export/direct",
            {"part_query": label, "include_preview": False},
            timeout=360,
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        result = {"status": "error", "error": f"HTTP {exc.code}: {body[:500]}"}
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}

    elapsed = round(time.time() - t0, 1)
    status = result.get("status")
    print(
        f"  status={status} cache_hit={result.get('cache_hit')} "
        f"part_label={result.get('part_label')!r} ({elapsed}s)",
        flush=True,
    )
    if status != "ok":
        print(f"  ERROR: {result.get('error')}", flush=True)
        return {**item, "status": "error", "error": result.get("error"), "elapsed_s": elapsed}

    glb_src = local_from_url(result.get("model_url"))
    anno_src = local_from_url(result.get("annotations_url"))
    ok_glb = copy_asset(glb_src, glb_dest)
    ok_anno = copy_asset(anno_src, anno_dest)
    size_mb = round(glb_dest.stat().st_size / (1024 * 1024), 3) if ok_glb else None
    if ok_glb and glb_dest.stat().st_size < 1024:
        print(f"  WARN tiny GLB ({glb_dest.stat().st_size} bytes) — treating as failed", flush=True)
        ok_glb = False
    print(f"  glb={ok_glb} ({size_mb} MB) anno={ok_anno} src={glb_src}", flush=True)
    return {
        **item,
        "status": "ok" if ok_glb else "error",
        "error": None if ok_glb else "failed to copy GLB / empty mesh",
        "part_label": result.get("part_label") or label,
        "model_file": f"models/{slug}.glb" if ok_glb else None,
        "annotations_file": f"annotations/{slug}.annotations.json" if ok_anno else None,
        "annotation_count": result.get("annotation_count"),
        "selected_objects": result.get("selected_objects") or [],
        "cache_hit": result.get("cache_hit"),
        "size_mb": size_mb,
        "elapsed_s": elapsed,
        "viewer_query": (
            f"viewer.html?model=models/{slug}.glb"
            f"&annotations=annotations/{slug}.annotations.json"
            f"&title={urllib.parse.quote(item['de'])}"
            if ok_glb
            else None
        ),
    }

def sync_viewer() -> None:
    """Copy a self-contained viewer into the Pages folder."""
    dest_viewer = OUT / "viewer.html"
    dest_css = OUT / "styles.css"
    dest_js = OUT / "viewer.js"
    dest_vendor = OUT / "vendor"

    html = (VIEWER_SRC / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"\./styles\.css\?v=[^\"']+", "./styles.css", html)
    html = re.sub(r"\./viewer\.js\?v=[^\"']+", "./viewer.js", html)
    dest_viewer.write_text(html, encoding="utf-8")
    shutil.copy2(VIEWER_SRC / "styles.css", dest_css)

    js = (VIEWER_SRC / "viewer.js").read_text(encoding="utf-8")
    js = js.replace(
        'const fallbackModel     = "../exports/glb/liver_test.glb";',
        'const fallbackModel     = "./models/leber.glb";',
    )
    js = js.replace(
        'const fallbackAnno      = "../exports/annotations/liver_test.annotations.json";',
        'const fallbackAnno      = "./annotations/leber.annotations.json";',
    )
    if 'params.get("title")' not in js:
        inject = """
const pageTitleParam = params.get("title");
if (pageTitleParam && partTitle) {
  partTitle.textContent = pageTitleParam;
  document.title = pageTitleParam + " — Anatomy Viewer";
}
"""
        js = js.replace(
            'const labelsToggle   = document.getElementById("labels-toggle");',
            'const labelsToggle   = document.getElementById("labels-toggle");\n' + inject,
        )
    dest_js.write_text(js, encoding="utf-8")

    needed = [
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
    src_root = VIEWER_SRC / "vendor" / "three"
    for rel in needed:
        src = src_root / rel
        dst = dest_vendor / "three" / rel
        if not src.exists():
            print(f"  WARN missing vendor file: {src}", flush=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def write_structure_page(item: dict) -> Path:
    """Write a shareable HTML page that opens the offline viewer for one organ."""
    pages = OUT / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    slug = item["slug"]
    title = item["de"]
    model = f"models/{slug}.glb"
    anno = f"annotations/{slug}.annotations.json"
    viewer_url = (
        f"../viewer.html?model={urllib.parse.quote(model, safe='/')}"
        f"&annotations={urllib.parse.quote(anno, safe='/')}"
        f"&title={urllib.parse.quote(title)}"
    )
    html = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — 3D Z-Anatomy</title>
  <meta http-equiv="refresh" content="0; url={viewer_url}">
  <style>
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: "Segoe UI", system-ui, sans-serif; background: #0f1419; color: #e8eef4;
    }}
    a {{ color: #3d9a8b; font-size: 1.1rem; }}
    p {{ color: #9aa8b6; }}
  </style>
</head>
<body>
  <div style="text-align:center;padding:2rem">
    <h1>{title}</h1>
    <p>{item['en']} → <code>{item.get('part_label') or item['label']}</code></p>
    <p><a href="{viewer_url}">Open interactive 3D viewer</a></p>
    <p><a href="../index.html">← Back to gallery</a></p>
  </div>
</body>
</html>
"""
    path = pages / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    return path


def write_gallery(rows: list[dict]) -> None:
    cards = []
    for r in rows:
        page_href = f"pages/{r['slug']}.html"
        if r.get("status") == "ok" and r.get("model_file"):
            status_html = f'<span class="ok">{r.get("size_mb", "?")} MB</span>'
            link = (
                f'<a class="open" href="{page_href}">Open HTML page</a>'
                f' <a class="open secondary" href="{r["viewer_query"]}">Direct viewer</a>'
            )
            write_structure_page(r)
        else:
            status_html = '<span class="err">export failed</span>'
            link = '<span class="open disabled">Unavailable</span>'
        cards.append(
            f"""
      <article class="card">
        <h2>{r['de']}</h2>
        <p class="en">{r['en']}</p>
        <p class="label"><code>{r.get('part_label') or r['label']}</code></p>
        <p class="meta">{status_html}</p>
        <p class="files"><code>pages/{r['slug']}.html</code></p>
        {link}
      </article>"""
        )

    html = f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Professor Blender Retrieval Demo — Z-Anatomy 3D</title>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a222c;
      --text: #e8eef4;
      --muted: #9aa8b6;
      --accent: #3d9a8b;
      --err: #c45c5c;
      --ok: #6bbf8a;
      --line: #2a3542;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: radial-gradient(1200px 600px at 10% -10%, #1c2a33, var(--bg));
      color: var(--text);
      min-height: 100vh;
    }}
    header {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 2.5rem 1.25rem 1rem;
    }}
    header h1 {{
      margin: 0 0 0.5rem;
      font-size: clamp(1.6rem, 3vw, 2.2rem);
      font-weight: 650;
      letter-spacing: -0.02em;
    }}
    header p {{
      margin: 0.35rem 0;
      color: var(--muted);
      max-width: 52rem;
      line-height: 1.5;
    }}
    .grid {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 1rem 1.25rem 3rem;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 1rem;
    }}
    .card {{
      background: color-mix(in srgb, var(--panel) 92%, black);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 1.1rem 1.15rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}
    .card h2 {{ margin: 0; font-size: 1.15rem; }}
    .en {{ margin: 0; color: var(--muted); font-size: 0.92rem; }}
    .label code, .files code {{
      font-size: 0.78rem;
      color: #b7c7d6;
      word-break: break-word;
    }}
    .meta {{ margin: 0.25rem 0 0.5rem; font-size: 0.85rem; }}
    .ok {{ color: var(--ok); }}
    .err {{ color: var(--err); }}
    .open {{
      margin-top: 0.35rem;
      display: inline-block;
      text-decoration: none;
      color: #06241f;
      background: var(--accent);
      padding: 0.45rem 0.8rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.9rem;
      width: fit-content;
      margin-right: 0.4rem;
    }}
    .open.secondary {{ background: #2a4050; color: #d7e6ef; }}
    .open:hover {{ filter: brightness(1.08); }}
    .open.disabled {{
      background: #3a4552;
      color: #9aa8b6;
      pointer-events: none;
    }}
    footer {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 0 1.25rem 2.5rem;
      color: var(--muted);
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Blender / Z-Anatomy retrieval examples</h1>
    <p>
      Offline HTML gallery for the professor test list.
      Each card has a dedicated HTML page under <code>pages/</code> plus an interactive Three.js viewer.
      No backend required — open <code>index.html</code> locally or publish this folder on GitHub Pages.
    </p>
  </header>
  <section class="grid">
    {''.join(cards)}
  </section>
  <footer>
    Tip: rotate with left drag, zoom with scroll, pan with right drag. Use Reset view if framing looks off.
  </footer>
</body>
</html>
"""
    (OUT / "index.html").write_text(html, encoding="utf-8")

    root = REPO / "docs" / "index.html"
    root.write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=./professor-blender-demo/">
  <title>ThesisBackend GitHub Pages</title>
</head>
<body>
  <p><a href="./professor-blender-demo/">Professor Blender 3D demo</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )

    readme = OUT / "README.md"
    readme.write_text(
        """# Professor Blender retrieval demo (static HTML)

Interactive 3D gallery for the German structure list.

## Show the professor (offline)

1. Open `docs/professor-blender-demo/index.html` in a browser  
   (or serve the folder: `python -m http.server 5500` from `docs/professor-blender-demo`).
2. Or open a single organ page, e.g. `pages/leber.html`.

Browsers may block `file://` module imports for Three.js. Prefer a tiny local server:

```powershell
cd docs\\professor-blender-demo
python -m http.server 5500
```

Then open http://127.0.0.1:5500/

## GitHub Pages

1. Commit the `docs/` folder.
2. GitHub → Settings → Pages → Deploy from branch → `/docs`.
3. URL: `https://AdarshRajDS.github.io/ThesisBackend/professor-blender-demo/`

## Rebuild

```bash
python scripts/build_professor_blender_gallery.py
```
""",
        encoding="utf-8",
    )



def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    ANNOS.mkdir(parents=True, exist_ok=True)

    # Health check
    try:
        with urllib.request.urlopen(f"{API}/anatomy/health", timeout=30) as resp:
            health = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"Backend not ready at {API}: {exc}", file=sys.stderr)
        return 1
    if not health.get("ready"):
        print(f"Anatomy MCP not ready: {health}", file=sys.stderr)
        return 1
    print("Backend ready.", flush=True)

    rows = [export_one(item) for item in STRUCTURES]
    sync_viewer()
    write_gallery(rows)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "api": API,
        "items": rows,
        "pages_url_hint": "https://AdarshRajDS.github.io/ThesisBackend/professor-blender-demo/",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    ok = sum(1 for r in rows if r.get("status") == "ok")
    print(f"\nDone: {ok}/{len(rows)} exports OK → {OUT}", flush=True)

    # Zip for easy handoff to the professor
    zip_path = REPO / "docs" / "professor-blender-demo.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", OUT)
    print(f"ZIP: {zip_path} ({round(zip_path.stat().st_size / (1024 * 1024), 2)} MB)", flush=True)
    return 0 if ok == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
