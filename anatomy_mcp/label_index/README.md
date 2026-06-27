# Anatomy label index

| File | Role |
|------|------|
| `exportable_catalog.json` | **Primary matcher** — only entries with exportable geometry (built from `Startup.blend`). Used by `search_anatomy_catalog` and export tools. |
| `z_anatomy_index.json` | **Fallback / debug** — full scene index. Used only if the exportable catalog is missing. |

## Regenerate catalog

```powershell
$env:BLENDER_BIN
$env:Z_ANATOMY_BLEND
& $env:BLENDER_BIN --background $env:Z_ANATOMY_BLEND `
  --python anatomy_mcp\blender_scripts\build_exportable_catalog.py
```

Or: `.\scripts\rebuild_exportable_catalog.ps1`

## Rich labels on every export

Z-Anatomy label objects use suffixes such as **`.t`** (text), **`.j`** (marker). Exports now:

1. Collect label objects in the same collections / parent hierarchy as the exported organ  
2. Merge **`exports/scene_scan/annotations_full.json`** when you have run the scan script (recommended once)  
3. Add a **fallback label** (organ name at model center) if nothing else matches — so `annotation_count` is never 0  

Build the annotation scan:

```powershell
& $env:BLENDER_BIN --background $env:Z_ANATOMY_BLEND `
  --python anatomy_mcp\blender_scripts\scan_annotations_full.py
```

After changing label logic, re-export organs (cache schema **v4** skips old zero-label caches).
