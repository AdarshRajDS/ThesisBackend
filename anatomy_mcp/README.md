# anatomy-blender-mcp

Windows-local Python MVP for exporting Z-Anatomy parts through a real Model Context Protocol server.

This project exposes one real MCP tool:

`export_anatomy_part`

Manual Blender commands are for testing only. Production chatbot or agent integration must call the MCP tool `export_anatomy_part`.

## What It Does

The workflow is:

`MCP client -> export_anatomy_part -> Blender CLI -> Startup.blend -> clean GLB + annotation JSON + optional PNG`

The server does not accept arbitrary `.blend` paths, Python code, Blender operators, or output paths. It always uses the configured Z-Anatomy source file and exports only the resolved part selection.

The primary output is now:

- a clean GLB for geometry
- a structured annotation JSON file
- a small custom web viewer that reads both

## Project Layout

```text
C:\Users\Admin\Documents\blendermcp\
  server.py
  config.py
  requirements.txt
  README.md

  blender_scripts\
    scan_z_anatomy.py
    build_exportable_catalog.py
    export_part.py

  label_index\
    .gitkeep
    z_anatomy_index.json
    exportable_catalog.json

  exports\
    glb\
    annotations\
    preview\

  logs\
    exports.log

  viewer\
    index.html
    styles.css
    viewer.js
    dev_server.js
```

## Prerequisites

- Windows
- Blender installed at `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`
- Z-Anatomy installed at `C:\Users\Admin\Downloads\Z-Anatomy (1)\Z-Anatomy\Startup.blend`
- Standard Python installed and available as `python`

Default Blender timeouts are configured in [config.py](C:/Users/Admin/Documents/blendermcp/config.py:1):

- `BLENDER_EXPORT_TIMEOUT_SECONDS = 300`
- `BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS = 900`

Increase those if large anatomy structures like thalamus or brain still time out on your machine.

Install dependencies:

```powershell
cd C:\Users\Admin\Documents\blendermcp
python -m pip install -r requirements.txt
```

## Test Blender Version

Verified locally:

```text
Blender 5.1.1
```

Command:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --version
```

## Generate The Label Index

```powershell
cd C:\Users\Admin\Documents\blendermcp

& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  "C:\Users\Admin\Downloads\Z-Anatomy (1)\Z-Anatomy\Startup.blend" `
  --python "C:\Users\Admin\Documents\blendermcp\blender_scripts\scan_z_anatomy.py"
```

Expected stdout includes:

```text
WROTE_INDEX: C:\Users\Admin\Documents\blendermcp\label_index\z_anatomy_index.json
COLLECTION_COUNT: ...
OBJECT_COUNT: ...
```

## Search The Index Manually

```powershell
Select-String -Path C:\Users\Admin\Documents\blendermcp\label_index\z_anatomy_index.json -Pattern "liver"
Select-String -Path C:\Users\Admin\Documents\blendermcp\label_index\z_anatomy_index.json -Pattern "heart"
Select-String -Path C:\Users\Admin\Documents\blendermcp\label_index\z_anatomy_index.json -Pattern "brain"
```

## Generate The Exportable Catalog

The raw label index says whether a name exists in the Blender scene. The exportable catalog says whether that name has real exportable geometry. Generate it after scanning the Z-Anatomy file:

```powershell
cd C:\Users\Admin\Documents\blendermcp

& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  "C:\Users\Admin\Downloads\Z-Anatomy (1)\Z-Anatomy\Startup.blend" `
  --python "C:\Users\Admin\Documents\blendermcp\blender_scripts\build_exportable_catalog.py"
```

Expected stdout includes:

```text
WROTE_EXPORTABLE_CATALOG: C:\Users\Admin\Documents\blendermcp\label_index\exportable_catalog.json
ENTRY_COUNT: ...
COLLECTION_ENTRY_COUNT: ...
OBJECT_ENTRY_COUNT: ...
```

When `exportable_catalog.json` exists, the MCP resolver uses it first. Broad lateral queries such as `kidney` or `iris` return clear ambiguity instead of trying a non-exportable collection. Specific queries such as `left kidney`, `right kidney`, `left iris`, or `Iris.l` resolve to exportable objects.

## Test The Export Script Manually

After finding a real object name in the index:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  "C:\Users\Admin\Downloads\Z-Anatomy (1)\Z-Anatomy\Startup.blend" `
  --python "C:\Users\Admin\Documents\blendermcp\blender_scripts\export_part.py" `
  -- `
  --part-label "liver" `
  --object-names "Liver" `
  --out "C:\Users\Admin\Documents\blendermcp\exports\glb\liver_test.glb" `
  --preview "C:\Users\Admin\Documents\blendermcp\exports\preview\liver_test.png"
```

Expected:

```text
exports\glb\liver_test.glb exists
exports\preview\liver_test.png exists
```

## Serve Export Files

Run the bundled Node static server from the project root:

```powershell
cd C:\Users\Admin\Documents\blendermcp
node viewer\dev_server.js
```

This makes exported files available at URLs like:

```text
http://localhost:8123/exports/glb/liver_abc12345.glb
http://localhost:8123/exports/annotations/liver_abc12345.annotations.json
http://localhost:8123/viewer/index.html?model=http://localhost:8123/exports/glb/liver_abc12345.glb&annotations=http://localhost:8123/exports/annotations/liver_abc12345.annotations.json
```

## Run The MCP Server

Start the real MCP server over `stdio`:

```powershell
cd C:\Users\Admin\Documents\blendermcp
python server.py
```

## Validate MCP Tool Discovery

Use any MCP client or inspector that supports `stdio` servers and point it at:

```text
python C:\Users\Admin\Documents\blendermcp\server.py
```

The client should list these tools:

```text
search_anatomy_catalog
export_anatomy_part
export_anatomy_package
```

## Validate MCP Tool Invocation

Call the tool with:

```json
{
  "part_query": "liver",
  "include_preview": false
}
```

Expected shape:

```json
{
  "model_url": "http://localhost:8123/exports/glb/liver_abc12345.glb",
  "annotations_url": "http://localhost:8123/exports/annotations/liver_abc12345.annotations.json",
  "viewer_url": "http://localhost:8123/viewer/index.html?model=http://localhost:8123/exports/glb/liver_abc12345.glb&annotations=http://localhost:8123/exports/annotations/liver_abc12345.annotations.json",
  "preview_url": null,
  "part_label": "liver",
  "source_blend": "Startup.blend",
  "selected_objects": ["Liver"],
  "annotation_labels": [
    "Anterior lateral segment of liver (VI)",
    "Left lobe of liver"
  ],
  "annotation_count": 8
}
```

## Annotation JSON

The sidecar JSON contains annotation entries with stable IDs, visible label text, and world-space anchor positions. The custom web viewer projects those anchors into screen space and renders readable HTML labels over the clean GLB.

Example shape:

```json
{
  "part_label": "liver",
  "selected_objects": ["Liver"],
  "model_space": {
    "center": [-0.01, -0.02, 1.17],
    "size": [0.20, 0.15, 0.16]
  },
  "annotations": [
    {
      "id": "liver-01",
      "index": 1,
      "label": "Left posterior lateral segment of liver (II)",
      "source_object": "Left posterior lateral segment of liver (II)",
      "anchor_world": [0.0, 0.0, 0.0],
      "anchor_relative": [0.0, 0.0, 0.0],
      "object_type": "MESH"
    }
  ]
}
```

## Error Responses

Not found:

```json
{
  "error": "part_not_found",
  "part_query": "neuromuscular junction"
}
```

Ambiguous:

```json
{
  "error": "ambiguous_part",
  "part_query": "kidney",
  "matches": ["left_kidney", "right_kidney"]
}
```

Index missing:

```json
{
  "error": "index_not_found",
  "instruction": "Run the scan_z_anatomy.py Blender command first."
}
```

## Logging

Each export request is written as a JSON line to:

`C:\Users\Admin\Documents\blendermcp\logs\exports.log`

Each entry includes timestamp, normalized query, resolver result, output filenames, Blender exit code when available, duration, and final status.

## Safety Boundaries

- Accepted inputs are `part_query`, `include_preview`, and optional `region_hint`
- Arbitrary `.blend` paths are not accepted
- Arbitrary Python code is not accepted
- Arbitrary output paths are not accepted
- Full-scene export is not allowed by default
- Blender subprocess calls use a 180 second timeout

## Notes

- `include_preview=false` still exports the GLB and returns `preview_url: null`
- If `label_index/z_anatomy_index.json` is missing, the server returns an error instead of auto-generating it
- To move this project later to `C:\Users\Admin\anatomy-blender-mcp`, update `PROJECT_ROOT` in `config.py`
