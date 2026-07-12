import argparse
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from blender_paths import SCENE_SCAN_DIR
from export_utils import (
    extract_custom_properties,
    serialize_bound_box,
    serialize_matrix,
    serialize_vector,
    utc_timestamp,
    write_json,
)


ANNOTATIONS_SCAN_PATH = SCENE_SCAN_DIR / "annotations_full.json"

EXPORTABLE_TYPES = {"MESH", "CURVE", "SURFACE"}
ANNOTATION_SUFFIXES = (".j", ".t", ".g", ".i", ".s")
PREVIEW_LIGHT_NAME = "MCP_PreviewLight"
PREVIEW_TARGET_NAME = "MCP_PreviewTarget"
PREVIEW_CAMERA_NAME = "MCP_PreviewCamera"
WEB_SAFE_MATERIAL_PREFIX = "MCP_WEBSAFE__"
WEB_MATERIAL_LIBRARY = {
    "heart": {"base_color": (0.55, 0.035, 0.025, 1.0), "roughness": 0.62, "metallic": 0.0},
    "artery": {"base_color": (0.85, 0.02, 0.015, 1.0), "roughness": 0.48, "metallic": 0.0},
    "vein": {"base_color": (0.08, 0.16, 0.55, 1.0), "roughness": 0.55, "metallic": 0.0},
    "cartilage": {"base_color": (0.72, 0.84, 0.90, 1.0), "roughness": 0.70, "metallic": 0.0},
    "ligament": {"base_color": (0.86, 0.78, 0.62, 1.0), "roughness": 0.82, "metallic": 0.0},
    "bone": {"base_color": (0.92, 0.88, 0.78, 1.0), "roughness": 0.84, "metallic": 0.0},
    "nerve": {"base_color": (0.90, 0.76, 0.34, 1.0), "roughness": 0.66, "metallic": 0.0},
    "muscle": {"base_color": (0.64, 0.08, 0.07, 1.0), "roughness": 0.64, "metallic": 0.0},
    "brain": {"base_color": (0.78, 0.66, 0.63, 1.0), "roughness": 0.72, "metallic": 0.0},
    "thalamus": {"base_color": (0.79, 0.64, 0.62, 1.0), "roughness": 0.72, "metallic": 0.0},
    "kidney": {"base_color": (0.42, 0.17, 0.15, 1.0), "roughness": 0.68, "metallic": 0.0},
    "liver": {"base_color": (0.52, 0.19, 0.12, 1.0), "roughness": 0.67, "metallic": 0.0},
    "default_soft_tissue": {"base_color": (0.60, 0.12, 0.10, 1.0), "roughness": 0.65, "metallic": 0.0},
}
PROFILE_KEYWORDS = {
    "heart": ("heart", "myocard", "atrium", "ventricle", "cardiac"),
    "artery": ("artery", "aorta", "arterial"),
    "vein": ("vein", "vena", "venous"),
    "cartilage": ("cartilage",),
    "ligament": ("ligament", "tendon", "leaflet", "valve", "fibrous"),
    "bone": ("bone", "osse", "vertebra", "rib", "sternum", "skull"),
    "nerve": ("nerve", "neural", "ganglion"),
    "muscle": ("muscle", "papillary", "myo"),
    "brain": ("brain", "cortex", "cerebr", "cerebell", "thalam"),
    "thalamus": ("thalam",),
    "kidney": ("kidney", "renal"),
    "liver": ("liver", "hepatic"),
}


def parse_bool(value):
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--blend-path")
    parser.add_argument("--part-label", required=True)
    parser.add_argument("--object-names", default="")
    parser.add_argument("--collection-names", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--include-subparts", type=parse_bool, default=True)
    parser.add_argument("--include-original-materials", type=parse_bool, default=True)
    parser.add_argument("--include-per-object-glb", type=parse_bool, default=False)
    parser.add_argument("--include-preview", type=parse_bool, default=False)
    parser.add_argument("--query", default="")
    parser.add_argument("--match-type", default="")
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


def slugify(value):
    safe = []
    for char in normalize_label(value):
        safe.append(char if char.isalnum() or char == "_" else "_")
    return "".join(safe).strip("_") or "item"


def ensure_principled_material(name, base_color, roughness=0.65, metallic=0.0):
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
    shader_node.inputs["Roughness"].default_value = roughness
    if "Metallic" in shader_node.inputs:
        shader_node.inputs["Metallic"].default_value = metallic
    if "Alpha" in shader_node.inputs:
        shader_node.inputs["Alpha"].default_value = base_color[3]

    node_tree.links.new(shader_node.outputs["BSDF"], output_node.inputs["Surface"])
    material.diffuse_color = base_color
    return material


def semantic_tokens_for_object(obj, part_label):
    tokens = [part_label, obj.name]
    tokens.extend(collection.name for collection in obj.users_collection)
    tokens.extend(parent_chain_names(obj))
    for slot in obj.material_slots:
        if slot.material is not None:
            tokens.append(slot.material.name)
    custom_properties = extract_custom_properties(obj)
    tokens.extend(str(key) for key in custom_properties.keys())
    tokens.extend(str(value) for value in custom_properties.values())
    return normalize_label(" ".join(token for token in tokens if token))


def material_profile_key_for_object(obj, part_label):
    tokens = semantic_tokens_for_object(obj, part_label)
    for profile_name, keywords in PROFILE_KEYWORDS.items():
        if any(keyword in tokens for keyword in keywords):
            return profile_name
    return "default_soft_tissue"


def apply_web_safe_materials(target_objects, part_label):
    changed = []
    for obj in target_objects:
        if obj.type != "MESH":
            continue
        profile_key = material_profile_key_for_object(obj, part_label)
        profile = WEB_MATERIAL_LIBRARY[profile_key]
        material = ensure_principled_material(
            f"{WEB_SAFE_MATERIAL_PREFIX}{profile_key}__{slugify(obj.name)}",
            profile["base_color"],
            roughness=profile["roughness"],
            metallic=profile["metallic"],
        )
        slots = list(obj.material_slots)
        if not slots:
            obj.data.materials.append(material)
        else:
            for slot in slots:
                slot.material = material
        changed.append({"object": obj.name, "profile": profile_key, "material": material.name})
    return changed


def is_annotation_like_name(name):
    return name.endswith(ANNOTATION_SUFFIXES)


def object_center_world(obj):
    if obj.type == "MESH" and getattr(obj, "bound_box", None):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        if points:
            return sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    return obj.matrix_world.translation.copy()


def selected_bounds(objects):
    points = []
    for obj in objects:
        if obj.type == "MESH" and getattr(obj, "bound_box", None):
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


def gather_target_objects(object_names, collection_names, include_subparts):
    selected = {}

    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj is not None and obj.type in EXPORTABLE_TYPES and not is_annotation_like_name(obj.name):
            selected[obj.name] = obj
            if include_subparts:
                for child in obj.children_recursive:
                    if child.type in EXPORTABLE_TYPES and not is_annotation_like_name(child.name):
                        selected[child.name] = child

    for name in collection_names:
        collection = bpy.data.collections.get(name)
        if collection is None:
            continue
        for obj in collection.all_objects:
            if obj.type in EXPORTABLE_TYPES and not is_annotation_like_name(obj.name):
                selected[obj.name] = obj

    return list(selected.values())


def annotation_descendant_names(target_objects):
    names = set()
    for obj in target_objects:
        for child in obj.children_recursive:
            if is_annotation_like_name(child.name):
                names.add(child.name)
    return names


def parent_chain_names(obj):
    names = []
    current = obj.parent
    while current is not None:
        names.append(current.name)
        current = current.parent
    return names


def build_collection_parent_lookup():
    parents = {}
    for parent in bpy.data.collections:
        for child in parent.children:
            parents[child.name] = parent.name
    return parents


def collection_path(collection_name, parent_lookup):
    path = [collection_name]
    current_name = collection_name
    while current_name in parent_lookup:
        current_name = parent_lookup[current_name]
        path.append(current_name)
    path.reverse()
    return path


def mesh_stats(obj):
    if obj.type != "MESH" or obj.data is None:
        return {"vertices": 0, "edges": 0, "polygons": 0}
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "polygons": len(obj.data.polygons),
    }


def object_record(obj):
    world_matrix = obj.matrix_world.copy()
    return {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "children": sorted((child.name for child in obj.children), key=str.lower),
        "collections": sorted((collection.name for collection in obj.users_collection), key=str.lower),
        "custom_properties": extract_custom_properties(obj),
        "data_name": obj.data.name if obj.data else None,
        "material_slots": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "location": serialize_vector(obj.location),
        "rotation_mode": obj.rotation_mode,
        "rotation_euler": serialize_vector(obj.rotation_euler),
        "rotation_quaternion": serialize_vector(obj.rotation_quaternion),
        "scale": serialize_vector(obj.scale),
        "matrix_world": serialize_matrix(world_matrix),
        "hide_viewport": bool(obj.hide_viewport),
        "hide_render": bool(obj.hide_render),
        "bound_box_local": serialize_bound_box(getattr(obj, "bound_box", None)),
        "bound_box_world": serialize_bound_box(getattr(obj, "bound_box", None), world_matrix),
        "mesh_stats": mesh_stats(obj),
    }


def subset_collections(target_objects, explicit_collection_names):
    parent_lookup = build_collection_parent_lookup()
    collection_names = set(explicit_collection_names)

    for obj in target_objects:
        for collection in obj.users_collection:
            collection_names.add(collection.name)
            for ancestor in collection_path(collection.name, parent_lookup):
                collection_names.add(ancestor)

    records = []
    for name in sorted(collection_names, key=str.lower):
        collection = bpy.data.collections.get(name)
        if collection is None:
            continue
        records.append(
            {
                "name": collection.name,
                "parent": parent_lookup.get(collection.name),
                "children": sorted((child.name for child in collection.children), key=str.lower),
                "path": collection_path(collection.name, parent_lookup),
                "objects_direct": sorted((obj.name for obj in collection.objects), key=str.lower),
                "objects_recursive": sorted((obj.name for obj in collection.all_objects), key=str.lower),
                "custom_properties": extract_custom_properties(collection),
                "hide_viewport": bool(collection.hide_viewport),
                "hide_render": bool(collection.hide_render),
            }
        )
    return records


def relations_payload(collection_records, object_records):
    return {
        "object_to_collections": {
            item["name"]: item["collections"] for item in object_records
        },
        "collection_to_parent": {
            item["name"]: item["parent"] for item in collection_records
        },
        "parent_to_children_objects": {
            item["name"]: item["children"] for item in object_records if item["children"]
        },
    }


def load_annotation_scan():
    if not ANNOTATIONS_SCAN_PATH.exists():
        return []

    payload = json.loads(ANNOTATIONS_SCAN_PATH.read_text(encoding="utf-8"))
    return payload.get("annotations", [])


def filter_annotations(part_label, target_objects, explicit_collection_names, descendant_annotation_names):
    scan_annotations = load_annotation_scan()
    target_names = {obj.name for obj in target_objects}
    explicit_collection_names = set(explicit_collection_names)
    center, _ = selected_bounds(target_objects)

    candidates = []
    for item in scan_annotations:
        is_descendant_annotation = item["name"] in descendant_annotation_names
        source_obj = bpy.data.objects.get(item["name"])
        parent_related = False
        if source_obj is not None:
            parent_related = bool(target_names.intersection(parent_chain_names(source_obj)))
        linked_targets = [
            nearest["name"]
            for nearest in item.get("nearest_mesh_objects", [])
            if nearest.get("name") in target_names
        ]
        collection_overlap = explicit_collection_names.intersection(item.get("collections", []))
        if not is_descendant_annotation and not parent_related and not collection_overlap and not linked_targets:
            continue
        if linked_targets and not (parent_related or collection_overlap or is_descendant_annotation):
            continue

        anchor_world = Vector((0.0, 0.0, 0.0))
        bounds = item.get("bound_box_world") or []
        if bounds:
            points = [Vector(point) for point in bounds]
            anchor_world = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
        else:
            anchor_world = Vector(item.get("location") or [0.0, 0.0, 0.0])

        relative = anchor_world - center
        candidates.append(
            {
                "label": item.get("label_text_guess") or item["name"],
                "source_object": item["name"],
                "object_type": item["type"],
                "anchor_world": serialize_vector(anchor_world),
                "anchor_relative": serialize_vector(relative),
                "collections": item.get("collections", []),
                "custom_properties": item.get("custom_properties", {}),
                "classification": item.get("classification", "unknown"),
                "linked_targets": linked_targets,
            }
        )

    annotations = dedupe_annotations(candidates)
    for index, item in enumerate(annotations, start=1):
        item["id"] = f"{slugify(part_label)}-{index:03d}"
        item["index"] = index

    return {
        "part_label": part_label,
        "annotation_strategy": "full_scan_plus_local_filter",
        "annotations": annotations,
    }


def dedupe_annotations(candidates):
    priority = {
        "label": 0,
        "marker": 1,
        "helper": 2,
        "unknown": 3,
    }
    by_label = {}
    for item in candidates:
        key = normalize_label(item.get("label") or item.get("source_object") or "")
        if not key:
            continue
        existing = by_label.get(key)
        if existing is None:
            by_label[key] = item
            continue
        existing_rank = priority.get(existing.get("classification", "unknown"), 99)
        item_rank = priority.get(item.get("classification", "unknown"), 99)
        if item_rank < existing_rank:
            by_label[key] = item

    return [by_label[key] for key in sorted(by_label, key=str.lower)]


def ensure_camera():
    camera = bpy.data.objects.get(PREVIEW_CAMERA_NAME)
    if camera is not None and camera.type == "CAMERA":
        return camera

    camera_data = bpy.data.cameras.new(name=PREVIEW_CAMERA_NAME)
    camera = bpy.data.objects.new(PREVIEW_CAMERA_NAME, camera_data)
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


def _track_to(obj, target):
    for constraint in list(obj.constraints):
        obj.constraints.remove(constraint)
    constraint = obj.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


def _ensure_area_light(name, energy, size):
    light = bpy.data.objects.get(name)
    if light is None or light.type != "LIGHT":
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light = bpy.data.objects.new(name, light_data)
        bpy.context.scene.collection.objects.link(light)
    light.data.energy = energy
    if hasattr(light.data, "shape"):
        light.data.shape = "RECTANGLE"
    if hasattr(light.data, "size"):
        light.data.size = size
    if hasattr(light.data, "size_y"):
        light.data.size_y = size * 0.85
    light.hide_render = False
    try:
        light.hide_set(False)
    except Exception:
        pass
    return light


def ensure_preview_lights(center, max_dimension, target):
    """Soft 3-point studio rig (key + fill + rim) scaled to the part size."""
    scale = max(max_dimension, 0.1)
    base = 60.0 * (scale ** 2)

    key = _ensure_area_light(PREVIEW_LIGHT_NAME, energy=base * 3.0, size=scale * 3.0)
    key.location = center + Vector((scale * 1.8, -scale * 1.6, scale * 2.4))
    _track_to(key, target)

    fill = _ensure_area_light("MCP_PreviewFill", energy=base * 1.1, size=scale * 4.0)
    fill.location = center + Vector((-scale * 2.4, -scale * 1.2, scale * 0.6))
    _track_to(fill, target)

    rim = _ensure_area_light("MCP_PreviewRim", energy=base * 2.2, size=scale * 2.0)
    rim.location = center + Vector((scale * 0.4, scale * 2.6, scale * 1.8))
    _track_to(rim, target)

    return key


def _configure_preview_world(scene):
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("MCP_PreviewWorld")
        scene.world = world
    try:
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()
        bg = nodes.new(type="ShaderNodeBackground")
        out = nodes.new(type="ShaderNodeOutputWorld")
        bg.inputs["Color"].default_value = (0.09, 0.10, 0.12, 1.0)
        bg.inputs["Strength"].default_value = 1.0
        links.new(bg.outputs["Background"], out.inputs["Surface"])
    except Exception:
        world.color = (0.09, 0.10, 0.12)


def _configure_color_management(scene):
    view = scene.view_settings
    for transform in ("AgX", "Filmic"):
        try:
            view.view_transform = transform
            break
        except (TypeError, ValueError):
            continue
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "High Contrast"):
        try:
            view.look = look
            break
        except (TypeError, ValueError):
            continue
    try:
        view.exposure = 0.0
        view.gamma = 1.0
    except Exception:
        pass


def _configure_render_engine(scene):
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except (TypeError, ValueError):
            continue
    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        if hasattr(eevee, "taa_render_samples"):
            eevee.taa_render_samples = 128
        if hasattr(eevee, "use_gtao"):
            eevee.use_gtao = True
        if hasattr(eevee, "use_ssr"):
            eevee.use_ssr = True


def configure_preview(target_objects, preview_path):
    scene = bpy.context.scene
    camera = ensure_camera()
    center, size = selected_bounds(target_objects)
    target = ensure_preview_target(center)

    max_dimension = max(size.x, size.y, size.z, 0.1)
    distance = max_dimension * 4.0
    direction = Vector((1.45, -1.55, 0.95)).normalized()

    camera.location = center + (direction * distance)
    _track_to(camera, target)
    camera.data.lens = 52
    scene.camera = camera

    ensure_preview_lights(center, max_dimension, target)

    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(preview_path)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_freestyle = False
    if hasattr(scene.render, "use_compositing"):
        scene.render.use_compositing = False
    if hasattr(scene.render, "use_sequencer"):
        scene.render.use_sequencer = False

    _configure_render_engine(scene)
    _configure_preview_world(scene)
    _configure_color_management(scene)
    bpy.context.view_layer.update()


def set_selection(target_objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        obj.select_set(False)

    for obj in target_objects:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)

    bpy.context.view_layer.objects.active = target_objects[0] if target_objects else None


def isolate_scene_visibility(target_objects):
    target_names = {obj.name for obj in target_objects}
    target_names.update({
        PREVIEW_LIGHT_NAME,
        "MCP_PreviewFill",
        "MCP_PreviewRim",
        PREVIEW_TARGET_NAME,
        PREVIEW_CAMERA_NAME,
    })

    state = []
    view_layer_object_names = {obj.name for obj in bpy.context.view_layer.objects}
    for obj in bpy.data.objects:
        hidden = obj.hide_get() if obj.name in view_layer_object_names else None
        state.append((obj, bool(obj.hide_render), hidden))
        is_target = obj.name in target_names
        obj.hide_render = not is_target
        if obj.name in view_layer_object_names:
            obj.hide_set(not is_target)
    return state


def restore_scene_visibility(state):
    for obj, hide_render, hidden in state:
        obj.hide_render = hide_render
        if hidden is not None:
            obj.hide_set(hidden)


def export_glb_for_objects(objects, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    set_selection(objects)
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_apply=True,
    )


def render_preview():
    bpy.ops.render.render(write_still=True)


def package_manifest_payload(
    export_id,
    part_label,
    match_type,
    selected_objects,
    selected_collections,
    file_map,
):
    return {
        "export_id": export_id,
        "source_blend": bpy.data.filepath,
        "generated_at": utc_timestamp(),
        "part_label": part_label,
        "mode": "study",
        "resolved_by": match_type or "unknown",
        "selected_objects": selected_objects,
        "selected_collections": selected_collections,
        "files": file_map,
    }


def query_resolution_payload(args, selected_objects, selected_collections):
    match_type = args.match_type or ("collection" if args.collection_names else "object")
    matched_names = selected_collections if match_type == "collection" else selected_objects
    return {
        "query": args.query or args.part_label,
        "normalized_query": normalize_label(args.query or args.part_label),
        "match_type": match_type,
        "matched_names": matched_names,
        "part_label": args.part_label,
    }


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
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timings_path = out_dir / "timings.json"
    timer = StageTimer(timings_path)
    timer.mark("prepare_output_dir", out_dir=str(out_dir))
    open_blend_file_if_requested(args.blend_path, timer)

    object_names = split_names(args.object_names)
    collection_names = split_names(args.collection_names)
    if not object_names and not collection_names:
        json_result({"ok": False, "error": "no_target_names_provided", "part_label": args.part_label})
        return

    target_objects = gather_target_objects(object_names, collection_names, args.include_subparts)
    if not target_objects:
        json_result({"ok": False, "error": "no_objects_selected", "part_label": args.part_label})
        return
    timer.mark("gather_target_objects", selected_count=len(target_objects))

    selected_object_names = sorted((obj.name for obj in target_objects), key=str.lower)
    descendant_annotations = annotation_descendant_names(target_objects)
    timer.mark("annotation_descendants", descendant_count=len(descendant_annotations))
    collection_records = subset_collections(target_objects, collection_names)
    selected_collection_names = [item["name"] for item in collection_records]
    timer.mark("subset_collections", collection_count=len(collection_records))
    object_records = [object_record(obj) for obj in sorted(target_objects, key=lambda item: item.name.lower())]
    timer.mark("object_records", object_count=len(object_records))
    relations = relations_payload(collection_records, object_records)
    timer.mark("relations_payload")
    from annotation_discovery import build_annotation_payload

    annotations = build_annotation_payload(
        args.part_label,
        target_objects,
        object_names,
        collection_names,
    )
    timer.mark("filter_annotations", annotation_count=len(annotations["annotations"]))
    query_resolution = query_resolution_payload(args, selected_object_names, selected_collection_names)
    timer.mark("query_resolution")

    anatomy_glb_path = out_dir / "anatomy.glb"
    anatomy_original_materials_path = out_dir / "anatomy_original_materials.glb"
    annotations_path = out_dir / "annotations.json"
    objects_path = out_dir / "objects.json"
    collections_path = out_dir / "collections.json"
    relations_path = out_dir / "relations.json"
    query_resolution_path = out_dir / "query_resolution.json"
    package_manifest_path = out_dir / "package_manifest.json"
    preview_path = out_dir / "preview.png"

    if args.include_original_materials:
        export_glb_for_objects(target_objects, anatomy_original_materials_path)
        timer.mark("export_original_materials_glb", path=str(anatomy_original_materials_path))
    else:
        anatomy_original_materials_path = None

    web_material_objects = apply_web_safe_materials(target_objects, args.part_label)
    timer.mark(
        "apply_web_safe_materials",
        changed_count=len(web_material_objects),
        changed_objects=web_material_objects,
    )
    export_glb_for_objects(target_objects, anatomy_glb_path)
    timer.mark("export_anatomy_glb", path=str(anatomy_glb_path))

    if args.include_preview:
        visibility_state = isolate_scene_visibility(target_objects)
        try:
            configure_preview(target_objects, preview_path)
            timer.mark("configure_preview")
            render_preview()
            timer.mark("render_preview", path=str(preview_path))
        finally:
            restore_scene_visibility(visibility_state)
            timer.mark("restore_visibility")

    if args.include_per_object_glb:
        parts_dir = out_dir / "parts"
        for obj in sorted(target_objects, key=lambda item: item.name.lower()):
            export_glb_for_objects([obj], parts_dir / f"{slugify(obj.name)}.glb")
        timer.mark("export_per_object_glbs", parts_dir=str(parts_dir))
    else:
        parts_dir = None

    write_json(annotations_path, annotations)
    timer.mark("write_annotations_json", path=str(annotations_path))
    write_json(objects_path, {"objects": object_records})
    timer.mark("write_objects_json", path=str(objects_path))
    write_json(collections_path, {"collections": collection_records})
    timer.mark("write_collections_json", path=str(collections_path))
    write_json(relations_path, relations)
    timer.mark("write_relations_json", path=str(relations_path))
    write_json(query_resolution_path, query_resolution)
    timer.mark("write_query_resolution_json", path=str(query_resolution_path))

    file_map = {
        "anatomy_glb": anatomy_glb_path.relative_to(out_dir).as_posix(),
        "anatomy_original_materials_glb": anatomy_original_materials_path.relative_to(out_dir).as_posix()
        if anatomy_original_materials_path is not None
        else None,
        "annotations_json": annotations_path.relative_to(out_dir).as_posix(),
        "objects_json": objects_path.relative_to(out_dir).as_posix(),
        "collections_json": collections_path.relative_to(out_dir).as_posix(),
        "relations_json": relations_path.relative_to(out_dir).as_posix(),
        "preview_png": preview_path.relative_to(out_dir).as_posix() if args.include_preview else None,
        "timings_json": timings_path.relative_to(out_dir).as_posix(),
        "parts_dir": parts_dir.relative_to(out_dir).as_posix() if parts_dir is not None else None,
    }
    manifest = package_manifest_payload(
        out_dir.name,
        args.part_label,
        query_resolution["match_type"],
        selected_object_names,
        selected_collection_names,
        file_map,
    )
    write_json(package_manifest_path, manifest)
    timer.mark("write_package_manifest", path=str(package_manifest_path))
    timer.write_sidecar(current_stage="completed")

    json_result(
        {
            "ok": True,
            "export_id": out_dir.name,
            "part_label": args.part_label,
            "selected_objects": selected_object_names,
            "selected_collections": selected_collection_names,
            "annotation_count": len(annotations["annotations"]),
            "package_dir": str(out_dir),
            "package_manifest": str(package_manifest_path),
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
            }
        )
        raise
