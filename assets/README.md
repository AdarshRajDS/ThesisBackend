# Blender Assets

Place preloaded anatomy `.blend` files here for MCP asset rendering.

Expected filenames (based on current backend mapping):

- `brain.blend`
- `heart.blend`
- `hand.blend`
- `lung.blend`
- `spine.blend`

Worker container default lookup path is:

- `BLENDER_ASSETS_DIR=/code/assets`

You can override with environment variable `BLENDER_ASSETS_DIR`.

## Performance notes

Large `.blend` scenes can be slow in headless Docker CPU rendering.

Worker env toggles:

- `BLENDER_FAST_RENDER=true` (default): 512x512, lower samples for faster previews
- `BLENDER_FORCE_WORKBENCH=true` (default): force very fast workbench engine for huge scenes
- `BLENDER_ENABLE_AUTOEXEC=false` (default): keep disabled for template files that throw startup script errors
- `BLENDER_RENDER_TIMEOUT_SECONDS=900` (default): subprocess timeout for heavy scenes
