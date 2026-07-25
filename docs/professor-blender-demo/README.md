# Professor Blender retrieval demo (static HTML)

Interactive 3D gallery for the German structure list.

## Show the professor (offline)

1. Open `docs/professor-blender-demo/index.html` in a browser  
   (or serve the folder: `python -m http.server 5500` from `docs/professor-blender-demo`).
2. Or open a single organ page, e.g. `pages/leber.html`.

Browsers may block `file://` module imports for Three.js. Prefer a tiny local server:

```powershell
cd docs\professor-blender-demo
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
