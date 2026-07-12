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

# Lateral name suffixes seen in this Z-Anatomy Startup.blend. Top-level bones use
# .l/.r, but many sub-regions/landmarks use .i/.j as the paired suffix. All four
# are treated as "one member of a bilateral pair".
LATERAL_SUFFIXES = ("l", "r", "i", "j")


def geometry_counts(obj):
    """Return (vertex_count, polygon_count) for a renderable object, 0 if empty."""
    data = getattr(obj, "data", None)
    if data is None:
        return 0, 0
    try:
        if obj.type == "MESH":
            return len(data.vertices), len(data.polygons)
        if obj.type in {"CURVE", "SURFACE"}:
            verts = 0
            for spline in getattr(data, "splines", []):
                verts += len(getattr(spline, "points", []))
                verts += len(getattr(spline, "bezier_points", []))
            return verts, 0
    except Exception:
        return 0, 0
    return 0, 0


def object_has_geometry(obj):
    """True when the object carries actual renderable geometry (drops empty meshes)."""
    verts, polys = geometry_counts(obj)
    if obj.type == "MESH":
        return polys > 0 or verts > 0
    return verts > 0


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
    vertex_count, polygon_count = geometry_counts(obj)
    return {
        "id": f"object:{obj.name}",
        "label": obj.name,
        "normalized_label": normalize_label(obj.name),
        "match_type": "object",
        "object_names": [obj.name],
        "collection_names": [],
        "object_count": 1,
        "vertex_count": vertex_count,
        "polygon_count": polygon_count,
        "parent_collections": collection_names,
        "collection_paths": paths,
        "side": side_from_name(obj.name),
        "lateral_suffix": None,
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
        [
            obj
            for obj in collection.all_objects
            if obj.type in EXPORTABLE_TYPES and object_has_geometry(obj)
        ],
        key=lambda item: item.name.lower(),
    )
    object_names = [obj.name for obj in objects]
    paths = collection_paths(collection, parents)
    vertex_count = 0
    polygon_count = 0
    for obj in objects:
        verts, polys = geometry_counts(obj)
        vertex_count += verts
        polygon_count += polys
    return {
        "id": f"collection:{collection.name}",
        "label": collection.name,
        "normalized_label": normalize_label(collection.name),
        "match_type": "collection",
        "object_names": object_names,
        "collection_names": [collection.name],
        "object_count": len(object_names),
        "vertex_count": vertex_count,
        "polygon_count": polygon_count,
        "parent_collections": sorted(set(parents.get(collection.name, [])), key=str.lower),
        "collection_paths": paths,
        "side": side_from_name(collection.name),
        "lateral_suffix": None,
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


def split_lateral(normalized_label):
    """Return (base, suffix) when the label carries a lateral suffix/prefix, else (label, None)."""
    for suffix in LATERAL_SUFFIXES:
        marker = f"_{suffix}"
        if normalized_label.endswith(marker) and len(normalized_label) > len(marker):
            return normalized_label[: -len(marker)], suffix
    if normalized_label.startswith("left_"):
        return normalized_label[len("left_") :], "l"
    if normalized_label.startswith("right_"):
        return normalized_label[len("right_") :], "r"
    return normalized_label, None


def bbox_center_x(entry):
    bbox = entry.get("bbox")
    if not isinstance(bbox, dict):
        return None
    center = bbox.get("center")
    if not center:
        return None
    try:
        return float(center[0])
    except (TypeError, ValueError, IndexError):
        return None


def learn_positive_x_side(entries):
    """
    Self-calibrate the world-X -> anatomical-side convention from entries whose
    side is already known (.l/.r/left/right). Returns the anatomical side that
    sits on positive X, or None when there is not enough signal.
    """
    left_x = []
    right_x = []
    for entry in entries:
        center_x = bbox_center_x(entry)
        if center_x is None:
            continue
        if entry.get("side") == "left":
            left_x.append(center_x)
        elif entry.get("side") == "right":
            right_x.append(center_x)
    if not left_x or not right_x:
        return None
    mean_left = sum(left_x) / len(left_x)
    mean_right = sum(right_x) / len(right_x)
    if mean_left == mean_right:
        return None
    return "left" if mean_left > mean_right else "right"


def assign_sides_and_pairs(entries):
    """
    Mark bilateral pairs (.l/.r and .i/.j) and fill in side for suffixes the
    name alone can't decode (.i/.j) using the learned bounding-box convention.
    Authoritative name-based sides (.l/.r/left/right) are never overwritten.
    """
    positive_x_side = learn_positive_x_side(entries)
    negative_x_side = None
    if positive_x_side == "left":
        negative_x_side = "right"
    elif positive_x_side == "right":
        negative_x_side = "left"

    groups = {}
    for entry in entries:
        base, suffix = split_lateral(entry["normalized_label"])
        if suffix is None:
            continue
        entry["lateral_suffix"] = suffix
        groups.setdefault(base, []).append(entry)

    for members in groups.values():
        is_pair = len(members) >= 2
        for entry in members:
            entry["is_pair_candidate"] = is_pair

        if not is_pair or positive_x_side is None:
            continue

        with_x = [(bbox_center_x(entry), entry) for entry in members]
        with_x = [(x, entry) for x, entry in with_x if x is not None]
        if len(with_x) < 2:
            continue
        midpoint = sum(x for x, _ in with_x) / len(with_x)
        for center_x, entry in with_x:
            if entry.get("side") in {"left", "right"}:
                continue
            entry["side"] = positive_x_side if center_x >= midpoint else negative_x_side


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    parents = collection_parent_map()

    entries = []
    for collection in sorted(bpy.data.collections, key=lambda item: item.name.lower()):
        if any(
            obj.type in EXPORTABLE_TYPES and object_has_geometry(obj)
            for obj in collection.all_objects
        ):
            entry = collection_entry(collection, parents)
            if entry["object_count"] > 0:
                entries.append(entry)

    for obj in sorted(bpy.data.objects, key=lambda item: item.name.lower()):
        if obj.type in EXPORTABLE_TYPES and object_has_geometry(obj):
            entries.append(object_entry(obj, parents))

    assign_sides_and_pairs(entries)
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
