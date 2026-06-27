import argparse
from pathlib import Path
import sys
import math
import os


CAMERA_PRESETS = {
    "frontal-superior": (2.8, -2.8, 1.6, 68.0, 45.0),
    "lateral": (3.0, -2.0, 0.5, 78.0, 55.0),
    "dorsal": (1.5, -3.0, 1.0, 75.0, 30.0),
    "anterior": (4.0, -1.5, 0.5, 82.0, 65.0),
    "posterior": (0.0, -5.0, 1.0, 80.0, 0.0),
}


def _ensure_camera(bpy):
    scene = bpy.context.scene
    cam = scene.camera
    if cam is not None:
        return cam

    cams = [obj for obj in bpy.data.objects if obj.type == "CAMERA"]
    if cams:
        scene.camera = cams[0]
        return cams[0]

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def _apply_camera_preset(bpy, preset: str):
    scene = bpy.context.scene
    cam = _ensure_camera(bpy)
    x, y, z, pitch_deg, yaw_deg = CAMERA_PRESETS.get(
        preset, CAMERA_PRESETS["frontal-superior"]
    )
    cam.location = (x, y, z)
    cam.rotation_euler = (math.radians(pitch_deg), 0.0, math.radians(yaw_deg))
    scene.camera = cam


def _ensure_lighting(bpy):
    scene = bpy.context.scene
    has_light = any(obj.type == "LIGHT" for obj in bpy.data.objects)
    if has_light:
        return
    light_data = bpy.data.lights.new("Key", type="AREA")
    light_data.energy = 800
    light_data.size = 2.0
    light = bpy.data.objects.new("Key", light_data)
    scene.collection.objects.link(light)
    light.location = (3.0, -2.0, 4.0)


def _configure_render(bpy, output_path: Path):
    scene = bpy.context.scene
    fast_mode = os.getenv("BLENDER_FAST_RENDER", "true").lower() in ("1", "true", "yes")
    force_workbench = os.getenv("BLENDER_FORCE_WORKBENCH", "false").lower() in ("1", "true", "yes")
    if fast_mode:
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
    else:
        scene.render.resolution_x = 1024
        scene.render.resolution_y = 1024
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(output_path.with_suffix(""))

    # For very heavy files, workbench can avoid long Cycles startup/runtime.
    if force_workbench:
        engines = ("BLENDER_WORKBENCH", "BLENDER_EEVEE", "CYCLES")
    else:
        engines = ("CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH")

    for engine in engines:
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue

    if scene.render.engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 24 if fast_mode else 96
        scene.cycles.use_denoising = True


def main() -> None:
    try:
        sep_index = sys.argv.index("--")
        script_args = sys.argv[sep_index + 1 :]
    except ValueError:
        script_args = []

    parser = argparse.ArgumentParser(description="Render preloaded .blend asset.")
    parser.add_argument("--asset", required=True)
    parser.add_argument("--camera-preset", default="frontal-superior")
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-model", required=False, default=None)
    args = parser.parse_args(script_args)

    import bpy

    asset_path = Path(args.asset)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset_path}")

    # Open the asset scene in a stable way from factory startup.
    # This avoids app-template startup script side-effects in headless mode.
    bpy.ops.wm.open_mainfile(
        filepath=str(asset_path),
        load_ui=False,
        use_scripts=False,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    _apply_camera_preset(bpy, args.camera_preset)
    _ensure_lighting(bpy)
    _configure_render(bpy, output)
    bpy.ops.render.render(write_still=True)

    # Blender writes with extension when filepath is suffixless
    written = output.with_suffix("").with_suffix(".png")
    if written.exists() and written != output:
        written.rename(output)

    # Optional GLB export for interactive viewers.
    if args.output_model:
        model_path = Path(args.output_model)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(
            filepath=str(model_path),
            export_format="GLB",
            export_materials="EXPORT",
            export_yup=True,
            use_selection=False,
        )


if __name__ == "__main__":
    main()
