import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

from annotation_discovery import build_annotation_payload


EXPORTABLE_TYPES = {"MESH", "CURVE", "SURFACE"}
EXPORT_MATERIAL_PREFIX = "MCP_EXPORT_MATERIAL__"
PREVIEW_LIGHT_NAME = "MCP_PreviewLight"
PREVIEW_TARGET_NAME = "MCP_PreviewTarget"

DEFAULT_ORGAN_COLOR = (0.72, 0.38, 0.32, 1.0)
PART_COLOR_HINTS = {
    "liver": (0.69, 0.31, 0.23, 1.0),
    "heart": (0.70, 0.12, 0.18, 1.0),
    "kidney": (0.53, 0.24, 0.19, 1.0),
    "brain": (0.84, 0.73, 0.70, 1.0),
    "stomach": (0.77, 0.49, 0.55, 1.0),
    "pancreas": (0.88, 0.72, 0.47, 1.0),
    "skull": (0.90, 0.88, 0.81, 1.0),
}


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--blend-path")
    parser.add_argument("--object-names", default="")
    parser.add_argument("--collection-names", default="")
    parser.add_argument("--part-label", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--annotations-out")
    parser.add_argument("--preview")
    return parser.parse_args(argv)


def split_names(raw_value):
    return [item for item in (part.strip() for part in raw_value.split("|")) if item]


def json_result(payload):
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def open_blend_file_if_requested(blend_path, timer):
    if not blend_path:
        timer.mark("open_blend_skipped", current_file=bpy.data.filepath)
        return

    path = Path(blend_path)
    timer.mark("open_blend_start", blend_path=str(path))
    bpy.ops.wm.open_mainfile(filepath=str(path))
    timer.mark(
        "open_blend_complete",
        blend_path=str(path),
        collection_count=len(bpy.data.collections),
        object_count=len(bpy.data.objects),
    )


def normalize_label(value):
    return (
        value.lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("&", "_")
    )


def ensure_principled_material(name, base_color):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name=name)

    material.use_nodes = True
    node_tree = material.node_tree
    node_tree.nodes.clear()

    output_node = node_tree.nodes.new(type="ShaderNodeOutputMaterial")
    output_node.location = (300, 0)

    shader_node = node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
    shader_node.location = (0, 0)
    shader_node.inputs["Base Color"].default_value = base_color
    shader_node.inputs["Roughness"].default_value = 0.82
    shader_node.inputs["Specular IOR Level"].default_value = 0.25

    node_tree.links.new(shader_node.outputs["BSDF"], output_node.inputs["Surface"])
    material.diffuse_color = base_color
    return material


def guess_export_color(part_label):
    normalized = normalize_label(part_label)
    for key, color in PART_COLOR_HINTS.items():
        if key in normalized:
            return color
    return DEFAULT_ORGAN_COLOR


def gather_target_objects(object_names, collection_names):
    selected = {}

    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj is not None and obj.type in EXPORTABLE_TYPES:
            selected[obj.name] = obj

    for name in collection_names:
        collection = bpy.data.collections.get(name)
        if collection is None:
            continue
        for obj in collection.all_objects:
            if obj.type in EXPORTABLE_TYPES:
                selected[obj.name] = obj

    return list(selected.values())


def apply_export_materials(target_objects, part_label):
    export_material = ensure_principled_material(
        f"{EXPORT_MATERIAL_PREFIX}{normalize_label(part_label)}",
        guess_export_color(part_label),
    )

    for obj in target_objects:
        if obj.type != "MESH":
            continue
        if len(obj.material_slots) == 0:
            obj.data.materials.append(export_material)
            continue
        for slot in obj.material_slots:
            slot.material = export_material


def selected_bounds(objects):
    points = []
    for obj in objects:
        if obj.type == "MESH" and obj.bound_box:
            for corner in obj.bound_box:
                points.append(obj.matrix_world @ Vector(corner))
        else:
            points.append(obj.matrix_world.translation.copy())

    if not points:
        return Vector((0.0, 0.0, 0.0)), Vector((1.0, 1.0, 1.0))

    min_corner = Vector(
        (
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        )
    )
    max_corner = Vector(
        (
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        )
    )
    center = (min_corner + max_corner) / 2.0
    size = max_corner - min_corner
    return center, size


def set_scene_visibility(target_objects):
    target_names = {obj.name for obj in target_objects}
    target_names.update({PREVIEW_LIGHT_NAME, PREVIEW_TARGET_NAME, "MCP_PreviewCamera"})
    view_layer = bpy.context.view_layer
    view_layer_object_names = {obj.name for obj in view_layer.objects}

    bpy.ops.object.select_all(action="DESELECT")

    for obj in bpy.data.objects:
        is_target = obj.name in target_names
        obj.hide_render = not is_target
        if obj.name in view_layer_object_names:
            obj.hide_set(not is_target)
            obj.select_set(is_target)

    selectable_targets = [obj for obj in target_objects if obj.name in view_layer_object_names]
    active_object = selectable_targets[0] if selectable_targets else None
    view_layer.objects.active = active_object
    return selectable_targets


def ensure_camera():
    camera = bpy.data.objects.get("MCP_PreviewCamera")
    if camera is not None and camera.type == "CAMERA":
        return camera

    camera_data = bpy.data.cameras.new(name="MCP_PreviewCamera")
    camera = bpy.data.objects.new("MCP_PreviewCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    return camera


def ensure_preview_target(location):
    target = bpy.data.objects.get(PREVIEW_TARGET_NAME)
    if target is None:
        target = bpy.data.objects.new(PREVIEW_TARGET_NAME, None)
        target.empty_display_type = "PLAIN_AXES"
        bpy.context.scene.collection.objects.link(target)
    target.location = location
    return target


def ensure_preview_light():
    light = bpy.data.objects.get(PREVIEW_LIGHT_NAME)
    if light is not None and light.type == "LIGHT":
        return light

    light_data = bpy.data.lights.new(name=PREVIEW_LIGHT_NAME, type="AREA")
    light_data.energy = 2200
    light = bpy.data.objects.new(PREVIEW_LIGHT_NAME, light_data)
    bpy.context.scene.collection.objects.link(light)
    return light


def configure_preview(target_objects, preview_path):
    scene = bpy.context.scene
    camera = ensure_camera()
    light = ensure_preview_light()
    center, size = selected_bounds(target_objects)
    target = ensure_preview_target(center)

    max_dimension = max(size.x, size.y, size.z, 0.1)
    distance = max_dimension * 4.0
    direction = Vector((1.45, -1.55, 0.95)).normalized()

    camera.location = center + (direction * distance)
    for constraint in list(camera.constraints):
        camera.constraints.remove(constraint)
    camera_constraint = camera.constraints.new(type="TRACK_TO")
    camera_constraint.target = target
    camera_constraint.track_axis = "TRACK_NEGATIVE_Z"
    camera_constraint.up_axis = "UP_Y"
    camera.data.lens = 52
    scene.camera = camera

    light.location = center + Vector((max_dimension * 1.8, -max_dimension * 1.6, max_dimension * 2.6))
    for constraint in list(light.constraints):
        light.constraints.remove(constraint)
    light_constraint = light.constraints.new(type="TRACK_TO")
    light_constraint.target = target
    light_constraint.track_axis = "TRACK_NEGATIVE_Z"
    light_constraint.up_axis = "UP_Y"
    if hasattr(light.data, "shape"):
        light.data.shape = "RECTANGLE"
    if hasattr(light.data, "size"):
        light.data.size = max_dimension * 3.0
    if hasattr(light.data, "size_y"):
        light.data.size_y = max_dimension * 2.6

    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(preview_path)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.use_freestyle = False
    if hasattr(scene.render, "use_compositing"):
        scene.render.use_compositing = False
    if hasattr(scene.render, "use_sequencer"):
        scene.render.use_sequencer = False
    if hasattr(scene, "use_nodes"):
        scene.use_nodes = False
    scene.world.color = (0.17, 0.18, 0.20)
    bpy.context.view_layer.update()


def export_glb(out_path):
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format="GLB",
        use_selection=True,
    )


def render_preview():
    bpy.ops.render.render(write_still=True)


class StageTimer:
    def __init__(self, sidecar_path):
        self.started_at = time.perf_counter()
        self.last_checkpoint = self.started_at
        self.events = []
        self.sidecar_path = Path(sidecar_path)

    def mark(self, stage, **extra):
        now = time.perf_counter()
        event = {
            "event": "timing",
            "stage": stage,
            "elapsed_ms": round((now - self.last_checkpoint) * 1000, 2),
            "since_start_ms": round((now - self.started_at) * 1000, 2),
        }
        event.update(extra)
        self.events.append(event)
        self.write_sidecar(current_stage=stage)
        print(json.dumps(event, ensure_ascii=False), flush=True)
        self.last_checkpoint = now

    def write_sidecar(self, current_stage=None):
        self.sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "current_stage": current_stage,
            "stages": self.events,
            "total_ms": round((time.perf_counter() - self.started_at) * 1000, 2),
        }
        self.sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def payload(self):
        return {
            "stages": self.events,
            "total_ms": round((time.perf_counter() - self.started_at) * 1000, 2),
        }


def main():
    args = parse_args()
    out_path = Path(args.out)
    annotations_out = Path(args.annotations_out) if args.annotations_out else None
    preview_path = Path(args.preview) if args.preview else None
    timings_path = out_path.with_suffix(".timings.json")
    timer = StageTimer(timings_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if annotations_out is not None:
        annotations_out.parent.mkdir(parents=True, exist_ok=True)
    if preview_path is not None:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
    timer.mark("prepare_output_paths", glb_path=str(out_path))
    open_blend_file_if_requested(args.blend_path, timer)

    object_names = split_names(args.object_names)
    collection_names = split_names(args.collection_names)

    if not object_names and not collection_names:
        json_result(
            {
                "ok": False,
                "error": "no_target_names_provided",
                "part_label": args.part_label,
            }
        )
        return

    target_objects = gather_target_objects(object_names, collection_names)
    if not target_objects:
        json_result(
            {
                "ok": False,
                "error": "no_objects_selected",
                "part_label": args.part_label,
            }
        )
        return
    timer.mark("gather_target_objects", selected_count=len(target_objects))

    apply_export_materials(target_objects, args.part_label)
    timer.mark("apply_export_materials")
    selectable_targets = set_scene_visibility(target_objects)
    if not selectable_targets:
        json_result(
            {
                "ok": False,
                "error": "no_target_objects_in_view_layer",
                "part_label": args.part_label,
            }
        )
        return
    timer.mark("set_scene_visibility", selected_count=len(selectable_targets))

    annotation_payload = build_annotation_payload(
        args.part_label,
        selectable_targets,
        object_names,
        collection_names,
    )
    timer.mark(
        "build_annotation_payload",
        annotation_count=len(annotation_payload["annotations"]),
        annotation_strategy=annotation_payload.get("annotation_strategy"),
    )

    export_glb(out_path)
    timer.mark("export_glb", path=str(out_path))

    if annotations_out is not None:
        annotations_out.write_text(
            json.dumps(annotation_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        timer.mark("write_annotations_json", path=str(annotations_out))

    if preview_path is not None:
        configure_preview(selectable_targets, preview_path)
        timer.mark("configure_preview")
        render_preview()
        timer.mark("render_preview", path=str(preview_path))
    timer.write_sidecar(current_stage="completed")

    json_result(
        {
            "ok": True,
            "part_label": args.part_label,
            "selected_objects": annotation_payload["selected_objects"],
            "annotation_labels": [item["label"] for item in annotation_payload["annotations"]],
            "annotation_count": len(annotation_payload["annotations"]),
            "annotation_json_path": str(annotations_out) if annotations_out is not None else None,
            "glb_path": str(out_path),
            "preview_path": str(preview_path) if preview_path is not None else None,
            "timings_path": str(timings_path),
            "timings": timer.payload(),
        }
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - runs inside Blender
        json_result(
            {
                "ok": False,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            }
        )
        sys.exit(1)
