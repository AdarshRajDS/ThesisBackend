"""Discover Z-Anatomy label objects for export_part and export_study_package."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector

from blender_paths import SCENE_SCAN_DIR
from export_utils import serialize_vector

ANNOTATIONS_SCAN_PATH = SCENE_SCAN_DIR / "annotations_full.json"
ANNOTATION_SUFFIXES = (".j", ".t", ".g", ".i", ".s")
LABEL_SUFFIXES = (".t",)
MAX_NEAREST_LABEL_DISTANCE = 0.35


def normalize_label(value: str) -> str:
    return (
        value.lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("&", "_")
    )


def is_annotation_like_name(name: str) -> bool:
    return name.endswith(ANNOTATION_SUFFIXES)


def label_display_name(name: str) -> str:
    for suffix in ANNOTATION_SUFFIXES:
        if name.endswith(suffix):
            cleaned = name[: -len(suffix)].strip(" .[]()\"'")
            if cleaned:
                return cleaned
    return name


def object_center_world(obj) -> Vector:
    if obj.type == "MESH" and getattr(obj, "bound_box", None):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        if points:
            return sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    return obj.matrix_world.translation.copy()


def selected_bounds(objects) -> tuple[Vector, Vector]:
    points = []
    for obj in objects:
        if obj.type == "MESH" and getattr(obj, "bound_box", None):
            for corner in obj.bound_box:
                points.append(obj.matrix_world @ Vector(corner))
        else:
            points.append(obj.matrix_world.translation.copy())

    if not points:
        center = Vector((0.0, 0.0, 0.0))
        return center, Vector((1.0, 1.0, 1.0))

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


def parent_chain_names(obj) -> list[str]:
    names = []
    current = obj.parent
    while current is not None:
        names.append(current.name)
        current = current.parent
    return names


def build_collection_parent_lookup() -> dict[str, str]:
    parents = {}
    for parent in bpy.data.collections:
        for child in parent.children:
            parents[child.name] = parent.name
    return parents


def collection_path(collection_name: str, parent_lookup: dict[str, str]) -> list[str]:
    path = [collection_name]
    current_name = collection_name
    while current_name in parent_lookup:
        current_name = parent_lookup[current_name]
        path.append(current_name)
    path.reverse()
    return path


def scope_collection_names(
    target_objects,
    object_names: list[str],
    collection_names: list[str],
) -> set[str]:
    names = set(collection_names)
    for name in object_names:
        if bpy.data.collections.get(name) is not None:
            names.add(name)
    for obj in target_objects:
        for collection in obj.users_collection:
            names.add(collection.name)
    return names


def annotation_descendant_names(target_objects) -> set[str]:
    names = set()
    for obj in target_objects:
        for child in obj.children_recursive:
            if is_annotation_like_name(child.name):
                names.add(child.name)
    return names


def nearest_target_name(label_obj, target_objects, target_names: set[str]) -> str | None:
    label_center = object_center_world(label_obj)
    best_name = None
    best_distance = None
    for target in target_objects:
        distance = (object_center_world(target) - label_center).length
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_name = target.name
    if best_name is None or best_distance is None:
        return None
    _center, dimensions = selected_bounds(target_objects)
    threshold = max(dimensions.length * MAX_NEAREST_LABEL_DISTANCE, 0.05)
    if best_distance <= threshold:
        return best_name
    return None


def linked_to_targets(label_obj, target_names: set[str], scope_collections: set[str]) -> bool:
    if label_obj.name in target_names:
        return False
    if any(parent_name in target_names for parent_name in parent_chain_names(label_obj)):
        return True
    label_collections = {collection.name for collection in label_obj.users_collection}
    if label_collections.intersection(scope_collections):
        return True
    return False


def add_annotation_entry(
    entries: dict[str, dict],
    label_obj,
    part_label: str,
    center: Vector,
    linked_targets: list[str],
) -> None:
    key = normalize_label(label_display_name(label_obj.name))
    if not key:
        return
    anchor = object_center_world(label_obj)
    relative = anchor - center
    entries[key] = {
        "label": label_display_name(label_obj.name),
        "source_object": label_obj.name,
        "object_type": label_obj.type,
        "anchor_world": serialize_vector(anchor),
        "anchor_relative": serialize_vector(relative),
        "linked_targets": linked_targets,
        "classification": "label" if label_obj.name.endswith(LABEL_SUFFIXES) else "marker",
    }


def collect_scene_annotations(
    part_label: str,
    target_objects,
    object_names: list[str],
    collection_names: list[str],
) -> list[dict]:
    target_names = {obj.name for obj in target_objects}
    center, _ = selected_bounds(target_objects)
    scope_collections = scope_collection_names(target_objects, object_names, collection_names)
    entries: dict[str, dict] = {}

    for obj_name in annotation_descendant_names(target_objects):
        label_obj = bpy.data.objects.get(obj_name)
        if label_obj is None:
            continue
        add_annotation_entry(entries, label_obj, part_label, center, sorted(target_names))

    for collection_name in scope_collections:
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            continue
        for label_obj in collection.all_objects:
            if label_obj.type not in {"MESH", "CURVE", "SURFACE", "FONT", "EMPTY"}:
                continue
            if not is_annotation_like_name(label_obj.name) and label_obj.type not in {"FONT", "EMPTY"}:
                continue
            if label_obj.name in target_names:
                continue
            if not linked_to_targets(label_obj, target_names, scope_collections):
                nearest = nearest_target_name(label_obj, target_objects, target_names)
                if nearest is None:
                    continue
                linked = [nearest]
            else:
                linked = sorted(
                    {
                        name
                        for name in parent_chain_names(label_obj)
                        if name in target_names
                    }
                    or target_names
                )
            add_annotation_entry(entries, label_obj, part_label, center, linked)

    return list(entries.values())


def load_annotation_scan() -> list[dict]:
    if not ANNOTATIONS_SCAN_PATH.exists():
        return []
    payload = json.loads(ANNOTATIONS_SCAN_PATH.read_text(encoding="utf-8"))
    return payload.get("annotations", [])


def collect_scan_annotations(
    part_label: str,
    target_objects,
    collection_names: list[str],
    descendant_names: set[str],
) -> list[dict]:
    scan_annotations = load_annotation_scan()
    if not scan_annotations:
        return []

    target_names = {obj.name for obj in target_objects}
    explicit_collections = set(collection_names)
    center, _ = selected_bounds(target_objects)
    candidates: dict[str, dict] = {}

    for item in scan_annotations:
        is_descendant = item["name"] in descendant_names
        source_obj = bpy.data.objects.get(item["name"])
        parent_related = False
        if source_obj is not None:
            parent_related = bool(target_names.intersection(parent_chain_names(source_obj)))
        linked_targets = [
            nearest["name"]
            for nearest in item.get("nearest_mesh_objects", [])
            if nearest.get("name") in target_names
        ]
        collection_overlap = explicit_collections.intersection(item.get("collections", []))
        if not is_descendant and not parent_related and not collection_overlap and not linked_targets:
            continue
        if linked_targets and not (parent_related or collection_overlap or is_descendant):
            continue

        anchor_world = Vector((0.0, 0.0, 0.0))
        bounds = item.get("bound_box_world") or []
        if bounds:
            points = [Vector(point) for point in bounds]
            anchor_world = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
        else:
            anchor_world = Vector(item.get("location") or [0.0, 0.0, 0.0])

        label = item.get("label_text_guess") or label_display_name(item["name"])
        key = normalize_label(label)
        candidates[key] = {
            "label": label,
            "source_object": item["name"],
            "object_type": item.get("type", "unknown"),
            "anchor_world": serialize_vector(anchor_world),
            "anchor_relative": serialize_vector(anchor_world - center),
            "linked_targets": linked_targets,
            "classification": item.get("classification", "unknown"),
        }

    return list(candidates.values())


def ensure_minimum_labels(part_label: str, target_objects, annotations: list[dict]) -> list[dict]:
    if annotations:
        return annotations
    center, _ = selected_bounds(target_objects)
    return [
        {
            "label": part_label,
            "source_object": part_label,
            "object_type": "synthetic",
            "anchor_world": serialize_vector(center),
            "anchor_relative": serialize_vector(Vector((0.0, 0.0, 0.0))),
            "linked_targets": [obj.name for obj in target_objects],
            "classification": "synthetic",
        }
    ]


def build_annotation_payload(
    part_label: str,
    target_objects,
    object_names: list[str],
    collection_names: list[str],
) -> dict:
    descendant_names = annotation_descendant_names(target_objects)
    scene_entries = collect_scene_annotations(part_label, target_objects, object_names, collection_names)
    scan_entries = collect_scan_annotations(
        part_label,
        target_objects,
        collection_names,
        descendant_names,
    )

    merged: dict[str, dict] = {}
    for item in scene_entries + scan_entries:
        key = normalize_label(item.get("label") or item.get("source_object") or "")
        if not key:
            continue
        if key not in merged or item.get("classification") == "label":
            merged[key] = item

    annotations = ensure_minimum_labels(part_label, target_objects, list(merged.values()))
    for index, item in enumerate(annotations, start=1):
        item["id"] = f"{normalize_label(part_label)}-{index:03d}"
        item["index"] = index

    strategy_parts = ["scene_graph"]
    if scan_entries:
        strategy_parts.append("annotation_scan")
    if len(annotations) == 1 and annotations[0].get("classification") == "synthetic":
        strategy_parts.append("synthetic_fallback")

    return {
        "part_label": part_label,
        "selected_objects": [obj.name for obj in target_objects],
        "annotation_strategy": "+".join(strategy_parts),
        "annotations": annotations,
    }
