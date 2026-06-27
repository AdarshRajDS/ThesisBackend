import argparse
from pathlib import Path
import sys


def create_placeholder_preview(path: Path, prompt: str):
    """Emergency fallback only — only used if Blender itself crashes entirely."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    image = Image.new("RGBA", (1024, 1024), (240, 220, 210, 255))
    draw = ImageDraw.Draw(image)
    draw.text((50, 480), "Render failed — Blender error", fill="red")
    draw.text((50, 520), prompt[:80], fill="gray")
    image.save(path, format="PNG")


def set_material_input(bsdf, name_v4, name_v3, value):
    """
    Try setting a Principled BSDF input by Blender 4.x name first,
    fall back to the Blender 3.x name, then silently skip if neither exists.
    Protects against API renames between Blender versions.
    """
    for name in (name_v4, name_v3):
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return


def apply_brain_material(bpy, obj, base_color=(0.85, 0.68, 0.62, 1.0), roughness=0.65):
    mat = bpy.data.materials.new(name=f"Mat_{obj.name}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-300, 0)
    output.location = (0, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # Blender 4.0 renamed several Principled BSDF inputs.
    # set_material_input() tries the new name first, then the old name.
    set_material_input(bsdf, "Base Color",         "Base Color",  base_color)
    set_material_input(bsdf, "Roughness",          "Roughness",   roughness)
    set_material_input(bsdf, "Specular IOR Level", "Specular",    0.15)   # renamed in 4.0
    set_material_input(bsdf, "Subsurface Weight",  "Subsurface",  0.04)   # renamed in 4.0
    # "Subsurface Color" removed in Blender 4.0 — omitted intentionally

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def build_brain_mesh(bpy, quality: int):
    """
    Builds a brain-like mesh using:
    - UV sphere with Musgrave + Clouds displacement for gyri/sulci folds
    - BLEND texture displacement for the longitudinal fissure groove
    - Brainstem cylinder and cerebellum lobe
    No Boolean modifiers — they crash reliably in headless bpy contexts.
    """
    import math

    # ── Cortex ───────────────────────────────────────────────────────
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=128, ring_count=64, radius=1.0, location=(0, 0, 0)
    )
    brain = bpy.context.active_object
    brain.name = "Brain"
    brain.scale = (1.05, 0.88, 0.78)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    subsurf = brain.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = max(1, quality)
    subsurf.render_levels = max(2, quality + 1)

    # Large folds (gyri/sulci)
    fold_tex = bpy.data.textures.new("BrainFolds", type="MUSGRAVE")
    fold_tex.musgrave_type = "FBM"
    fold_tex.noise_scale = 0.6
    fold_tex.octaves = 6.0
    fold_tex.dimension_max = 1.2
    fold_tex.lacunarity = 2.0
    disp1 = brain.modifiers.new("BrainFolds", "DISPLACE")
    disp1.texture = fold_tex
    disp1.strength = 0.20
    disp1.texture_coords = "GLOBAL"
    disp1.direction = "NORMAL"

    # Fine surface detail
    detail_tex = bpy.data.textures.new("BrainDetail", type="CLOUDS")
    detail_tex.noise_scale = 0.20
    detail_tex.noise_depth = 4
    disp2 = brain.modifiers.new("BrainDetail", "DISPLACE")
    disp2.texture = detail_tex
    disp2.strength = 0.07
    disp2.texture_coords = "GLOBAL"
    disp2.direction = "NORMAL"

    # Longitudinal fissure (groove along midline) — via BLEND texture on X axis
    groove_tex = bpy.data.textures.new("Fissure", type="BLEND")
    groove_tex.progression = "LINEAR"
    groove_disp = brain.modifiers.new("Fissure", "DISPLACE")
    groove_disp.texture = groove_tex
    groove_disp.strength = -0.14
    groove_disp.texture_coords = "GLOBAL"
    groove_disp.direction = "X"

    # ── Brainstem ────────────────────────────────────────────────────
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24, radius=0.17, depth=0.50, location=(0, -0.50, -0.52)
    )
    stem = bpy.context.active_object
    stem.name = "Brainstem"
    stem.rotation_euler = (math.radians(18), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    stem.modifiers.new("Subsurf", "SUBSURF").levels = 2

    # ── Cerebellum ───────────────────────────────────────────────────
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48, ring_count=24, radius=0.40, location=(0, -0.80, -0.20)
    )
    cerebellum = bpy.context.active_object
    cerebellum.name = "Cerebellum"
    cerebellum.scale = (1.0, 0.68, 0.52)
    bpy.ops.object.transform_apply(scale=True)

    cb_tex = bpy.data.textures.new("CbFolds", type="MUSGRAVE")
    cb_tex.musgrave_type = "RIDGED_MULTIFRACTAL"
    cb_tex.noise_scale = 0.22
    cb_tex.octaves = 5.0
    cb_disp = cerebellum.modifiers.new("CbFolds", "DISPLACE")
    cb_disp.texture = cb_tex
    cb_disp.strength = 0.09
    cb_disp.texture_coords = "GLOBAL"
    cb_disp.direction = "NORMAL"

    return brain, stem, cerebellum


def setup_scene(bpy):
    import math
    scene = bpy.context.scene

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 85
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (2.8, -2.8, 1.6)
    cam.rotation_euler = (math.radians(68), 0, math.radians(45))
    scene.camera = cam

    key_d = bpy.data.lights.new("Key", type="AREA")
    key_d.energy = 700
    key_d.size = 2.0
    key = bpy.data.objects.new("Key", key_d)
    scene.collection.objects.link(key)
    key.location = (3.5, -2.5, 4.0)
    key.rotation_euler = (math.radians(45), 0, math.radians(30))

    fill_d = bpy.data.lights.new("Fill", type="AREA")
    fill_d.energy = 250
    fill_d.size = 3.0
    fill = bpy.data.objects.new("Fill", fill_d)
    scene.collection.objects.link(fill)
    fill.location = (-3.0, -1.0, 2.0)

    rim_d = bpy.data.lights.new("Rim", type="SPOT")
    rim_d.energy = 180
    rim_d.spot_size = math.radians(40)
    rim = bpy.data.objects.new("Rim", rim_d)
    scene.collection.objects.link(rim)
    rim.location = (0, 3.5, 2.5)
    rim.rotation_euler = (math.radians(-45), 0, 0)


def configure_render(bpy, preview_path: Path, quality: int):
    """
    Engine priority:
      1. CYCLES  — CPU path-tracing, works headlessly without any GPU/EGL.
                   The libEGL crash only affects EEVEE/Workbench.
      2. BLENDER_EEVEE — needs libEGL (now installed via Dockerfile fix).
      3. BLENDER_WORKBENCH — last resort, flat shading but always works.
    """
    scene = bpy.context.scene
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.film_transparent = False

    engine_set = False
    for engine_name in ("CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine_name
            print(f"Render engine: {engine_name}", flush=True)
            engine_set = True
            break
        except Exception as e:
            print(f"Engine {engine_name} unavailable: {e}", flush=True)

    if not engine_set:
        print("WARNING: No render engine could be set — render may fail", flush=True)

    if scene.render.engine == "CYCLES":
        # Force CPU — no CUDA/OptiX in Docker
        cycles = scene.cycles
        cycles.device = "CPU"
        cycles.samples = 64 * quality        # 128 for standard, 256 for high
        cycles.use_denoising = True
        print(f"Cycles samples: {cycles.samples}", flush=True)
    elif scene.render.engine == "BLENDER_EEVEE":
        try:
            scene.eevee.taa_render_samples = 32
        except AttributeError:
            pass

    # Blender auto-appends the file extension — pass path WITHOUT .png
    scene.render.filepath = str(preview_path.with_suffix(""))
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def generate_with_blender(prompt: str, quality: int, model_path: Path, preview_path: Path):
    print("Starting generate_with_blender", flush=True)
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    print("Building brain mesh...", flush=True)
    brain, stem, cerebellum = build_brain_mesh(bpy, quality)

    apply_brain_material(bpy, brain,      base_color=(0.85, 0.68, 0.62, 1.0), roughness=0.65)
    apply_brain_material(bpy, stem,       base_color=(0.78, 0.60, 0.55, 1.0), roughness=0.70)
    apply_brain_material(bpy, cerebellum, base_color=(0.82, 0.65, 0.60, 1.0), roughness=0.68)

    setup_scene(bpy)
    configure_render(bpy, preview_path, quality)

    print(f"Rendering to: {preview_path}", flush=True)
    bpy.ops.render.render(write_still=True)
    print("Render complete", flush=True)

    # Blender may write the file without the suffix we stripped — normalise
    written = preview_path.with_suffix("").with_suffix(".png")
    if written.exists() and written != preview_path:
        written.rename(preview_path)
        print(f"Renamed {written} -> {preview_path}", flush=True)

    print(f"Exporting GLB to: {model_path}", flush=True)
    bpy.ops.export_scene.gltf(
        filepath=str(model_path),
        export_format="GLB" if model_path.suffix.lower() == ".glb" else "GLTF_SEPARATE",
        export_materials="EXPORT",
        export_yup=True,
        use_selection=False,
    )
    print("Export complete", flush=True)


def main() -> None:
    print("sys.argv:", sys.argv, flush=True)

    try:
        sep_index = sys.argv.index("--")
        script_args = sys.argv[sep_index + 1:]
    except ValueError:
        script_args = []

    print("script_args:", script_args, flush=True)

    parser = argparse.ArgumentParser(description="Generate a 3D anatomy asset using Blender.")
    parser.add_argument("--prompt",         required=True)
    parser.add_argument("--quality",        type=int, default=2)
    parser.add_argument("--output-model",   required=True)
    parser.add_argument("--output-preview", required=False, default=None)

    args = parser.parse_args(script_args)

    model_path   = Path(args.output_model)
    preview_path = Path(args.output_preview) if args.output_preview else model_path.with_suffix(".png")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        generate_with_blender(args.prompt, args.quality, model_path, preview_path)
    except Exception as exc:
        print(f"generate_with_blender FAILED: {exc}", flush=True)
        import traceback
        traceback.print_exc()
        create_placeholder_preview(preview_path, args.prompt)
        if not model_path.exists():
            model_path.write_bytes(b"")


if __name__ == "__main__":
    main()