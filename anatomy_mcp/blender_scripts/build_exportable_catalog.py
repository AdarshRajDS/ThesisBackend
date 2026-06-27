import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from blender_paths import EXPORTABLE_CATALOG_PATH
from export_utils import extract_custom_properties, serialize_vector


OUTPUT_PATH = EXPORTABLE_CATALOG_PATH
EXPORTABLE_TYPES = {"MESH", "CURVE", "SURFACE"}


def normalize_label(value):
    import re

    normalized = value.lower().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def collection_parent_map():
    parents = {}
    for collection in bpy.data.collections:
        for child in collection.children:
            parents.setdefault(child.name, []).append(collection.name)
    return parents


def collection_paths(collection, parents):
    direct_parents = parents.get(collection.name, [])
    if not direct_parents:
        return [[collection.name]]

    paths = []
    for parent_name in direct_parents:
        parent = bpy.data.collections.get(parent_name)
        if parent is None:
            paths.append([parent_name, collection.name])
            continue
        for parent_path in collection_paths(parent, parents):
            paths.append([*parent_path, collection.name])
    return paths


def object_collection_paths(obj, parents):
    paths = []
    for collection in obj.users_collection:
        paths.extend(collection_paths(collection, parents))
    return paths


def side_from_name(name):
    normalized = normalize_label(name)
    left_markers = ("_l", "l_", "left")
    right_markers = ("_r", "r_", "right")

    if normalized.endswith("_l") or normalized.startswith(left_markers) or "_left_" in normalized:
        return "left"
    if normalized.endswith("_r") or normalized.startswith(right_markers) or "_right_" in normalized:
        return "right"
    return None


def object_bbox_world(obj):
    if not getattr(obj, "bound_box", None):
        return None

    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    if not points:
        return None

    min_point = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    max_point = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    center = (min_point + max_point) * 0.5
    size = max_point - min_point
    return {
        "min": serialize_vector(min_point),
        "max": serialize_vector(max_point),
        "center": serialize_vector(center),
        "size": serialize_vector(size),
    }


def combined_bbox(objects):
    boxes = [object_bbox_world(obj) for obj in objects]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None

    mins = [Vector(box["min"]) for box in boxes]
    maxes = [Vector(box["max"]) for box in boxes]
    min_point = Vector((min(point.x for point in mins), min(point.y for point in mins), min(point.z for point in mins)))
    max_point = Vector((max(point.x for point in maxes), max(point.y for point in maxes), max(point.z for point in maxes)))
    center = (min_point + max_point) * 0.5
    size = max_point - min_point
    return {
        "min": serialize_vector(min_point),
        "max": serialize_vector(max_point),
        "center": serialize_vector(center),
        "size": serialize_vector(size),
    }


def complexity_from_count(object_count):
    if object_count >= 250:
        return "very_high"
    if object_count >= 75:
        return "high"
    if object_count >= 20:
        return "medium"
    return "low"


def object_entry(obj, parents):
    collection_names = sorted({collection.name for collection in obj.users_collection}, key=str.lower)
    paths = object_collection_paths(obj, parents)
    return {
        "id": f"object:{obj.name}",
        "label": obj.name,
        "normalized_label": normalize_label(obj.name),
        "match_type": "object",
        "object_names": [obj.name],
        "collection_names": [],
        "object_count": 1,
        "parent_collections": collection_names,
        "collection_paths": paths,
        "side": side_from_name(obj.name),
        "is_pair_candidate": False,
        "estimated_complexity": "low",
        "bbox": object_bbox_world(obj),
        "custom_properties": extract_custom_properties(obj),
        "search_terms": sorted(
            {
                normalize_label(obj.name),
                *(normalize_label(name) for name in collection_names),
            }
        ),
    }


def collection_entry(collection, parents):
    objects = sorted(
        [obj for obj in collection.all_objects if obj.type in EXPORTABLE_TYPES],
        key=lambda item: item.name.lower(),
    )
    object_names = [obj.name for obj in objects]
    paths = collection_paths(collection, parents)
    return {
        "id": f"collection:{collection.name}",
        "label": collection.name,
        "normalized_label": normalize_label(collection.name),
        "match_type": "collection",
        "object_names": object_names,
        "collection_names": [collection.name],
        "object_count": len(object_names),
        "parent_collections": sorted(set(parents.get(collection.name, [])), key=str.lower),
        "collection_paths": paths,
        "side": side_from_name(collection.name),
        "is_pair_candidate": False,
        "estimated_complexity": complexity_from_count(len(object_names)),
        "bbox": combined_bbox(objects),
        "custom_properties": extract_custom_properties(collection),
        "search_terms": sorted(
            {
                normalize_label(collection.name),
                *(normalize_label(name) for name in object_names[:50]),
                *(normalize_label(name) for path in paths for name in path),
            }
        ),
    }


def mark_pair_candidates(entries):
    by_base = {}
    for entry in entries:
        normalized = entry["normalized_label"]
        side = entry.get("side")
        if side == "left":
            base = normalized.removeprefix("left_").removesuffix("_l")
        elif side == "right":
            base = normalized.removeprefix("right_").removesuffix("_r")
        else:
            continue
        by_base.setdefault(base, set()).add(side)

    paired_bases = {base for base, sides in by_base.items() if {"left", "right"}.issubset(sides)}
    for entry in entries:
        normalized = entry["normalized_label"]
        base = normalized.removeprefix("left_").removeprefix("right_").removesuffix("_l").removesuffix("_r")
        entry["is_pair_candidate"] = base in paired_bases


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    parents = collection_parent_map()

    entries = []
    for collection in sorted(bpy.data.collections, key=lambda item: item.name.lower()):
        if any(obj.type in EXPORTABLE_TYPES for obj in collection.all_objects):
            entries.append(collection_entry(collection, parents))

    for obj in sorted(bpy.data.objects, key=lambda item: item.name.lower()):
        if obj.type in EXPORTABLE_TYPES:
            entries.append(object_entry(obj, parents))

    mark_pair_candidates(entries)
    payload = {
        "source_blend": bpy.data.filepath,
        "schema_version": 1,
        "exportable_type_count": len(EXPORTABLE_TYPES),
        "entry_count": len(entries),
        "collection_entry_count": sum(1 for entry in entries if entry["match_type"] == "collection"),
        "object_entry_count": sum(1 for entry in entries if entry["match_type"] == "object"),
        "entries": entries,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"WROTE_EXPORTABLE_CATALOG: {OUTPUT_PATH}")
    print(f"ENTRY_COUNT: {payload['entry_count']}")
    print(f"COLLECTION_ENTRY_COUNT: {payload['collection_entry_count']}")
    print(f"OBJECT_ENTRY_COUNT: {payload['object_entry_count']}")


if __name__ == "__main__":
    main()
