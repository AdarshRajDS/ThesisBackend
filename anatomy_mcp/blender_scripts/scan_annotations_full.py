import csv
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from blender_paths import SCENE_SCAN_DIR
from export_utils import (
    extract_custom_properties,
    make_json_safe,
    serialize_bound_box,
    serialize_matrix,
    serialize_vector,
    utc_timestamp,
    write_json,
)


OUTPUT_DIR = SCENE_SCAN_DIR
ANNOTATIONS_JSON_PATH = OUTPUT_DIR / "annotations_full.json"
ANNOTATIONS_CSV_PATH = OUTPUT_DIR / "annotation_candidates.csv"

ANNOTATION_SUFFIXES = {
    ".t": "label",
    ".j": "marker",
    ".i": "marker",
    ".s": "marker",
    ".g": "helper",
}
KEYWORD_CLASSIFICATIONS = {
    "label": "label",
    "text": "label",
    "marker": "marker",
    "annotation": "label",
    "helper": "helper",
    "guide": "helper",
    "pointer": "marker",
}
MESH_TYPES = {"MESH", "CURVE", "SURFACE"}


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


def object_center_world(obj):
    if obj.type == "MESH" and getattr(obj, "bound_box", None):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        if points:
            return sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    return obj.matrix_world.translation.copy()


def suffix_for_name(name):
    for suffix in ANNOTATION_SUFFIXES:
        if name.endswith(suffix):
            return suffix
    return None


def label_text_guess(name):
    cleaned = name
    suffix = suffix_for_name(name)
    if suffix:
        cleaned = cleaned[: -len(suffix)]
    return cleaned.strip(" []()'\"") or name


def safe_text_value(value, fallback):
    try:
        if value is None:
            return fallback
        return make_json_safe(value)
    except Exception:
        return fallback


def classification_for_object(obj):
    suffix = suffix_for_name(obj.name)
    if suffix:
        return ANNOTATION_SUFFIXES[suffix]

    if obj.type == "FONT":
        return "label"
    if obj.type == "EMPTY":
        return "helper"

    lowered = obj.name.lower()
    for keyword, classification in KEYWORD_CLASSIFICATIONS.items():
        if keyword in lowered:
            return classification

    return "unknown"


def is_annotation_candidate(obj):
    if obj.type in {"FONT", "EMPTY"}:
        return True

    if suffix_for_name(obj.name):
        return True

    lowered = obj.name.lower()
    return any(keyword in lowered for keyword in KEYWORD_CLASSIFICATIONS)


def nearest_mesh_objects(obj, mesh_centers, limit=3):
    center = object_center_world(obj)
    distances = []
    for mesh_name, mesh_center in mesh_centers:
        distance = (mesh_center - center).length
        distances.append((mesh_name, distance))

    distances.sort(key=lambda item: item[1])
    nearest = []
    for mesh_name, distance in distances[:limit]:
        nearest.append(
            {
                "name": mesh_name,
                "distance": round(float(distance), 6),
            }
        )
    return nearest


def material_names(obj):
    return [slot.material.name for slot in obj.material_slots if slot.material]


def scan_annotation_candidates():
    parent_lookup = build_collection_parent_lookup()

    mesh_centers = []
    for obj in bpy.data.objects:
        if obj.type in MESH_TYPES:
            mesh_centers.append((obj.name, object_center_world(obj)))

    annotations = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name.lower()):
        if not is_annotation_candidate(obj):
            continue

        collections = sorted((collection.name for collection in obj.users_collection), key=str.lower)
        path_hints = [collection_path(name, parent_lookup) for name in collections]
        world_matrix = obj.matrix_world.copy()

        text_guess = None
        if obj.type == "FONT":
            body = None
            try:
                body = getattr(getattr(obj, "data", None), "body", None)
            except Exception:
                body = None
            text_guess = safe_text_value(body, label_text_guess(obj.name))
        else:
            text_guess = label_text_guess(obj.name)

        annotations.append(
            {
                "name": obj.name,
                "type": obj.type,
                "collections": collections,
                "path_hints": path_hints,
                "custom_properties": extract_custom_properties(obj),
                "location": serialize_vector(obj.location),
                "matrix_world": serialize_matrix(world_matrix),
                "bound_box_world": serialize_bound_box(getattr(obj, "bound_box", None), world_matrix),
                "label_text_guess": text_guess,
                "classification": classification_for_object(obj),
                "material_slots": material_names(obj),
                "nearest_mesh_objects": nearest_mesh_objects(obj, mesh_centers),
            }
        )

    return annotations


def write_csv(path, annotations):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "type",
                "classification",
                "collections",
                "label_text_guess",
                "nearest_mesh_names",
            ],
        )
        writer.writeheader()
        for item in annotations:
            writer.writerow(
                {
                    "name": item["name"],
                    "type": item["type"],
                    "classification": item["classification"],
                    "collections": " | ".join(item["collections"]),
                    "label_text_guess": item["label_text_guess"] or "",
                    "nearest_mesh_names": " | ".join(
                        nearest["name"] for nearest in item["nearest_mesh_objects"]
                    ),
                }
            )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    annotations = scan_annotation_candidates()

    payload = {
        "source_blend": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "generated_at": utc_timestamp(),
        "annotation_count": len(annotations),
        "annotations": annotations,
    }

    write_json(ANNOTATIONS_JSON_PATH, payload)
    write_csv(ANNOTATIONS_CSV_PATH, annotations)

    print(f"WROTE_ANNOTATIONS_JSON: {ANNOTATIONS_JSON_PATH}")
    print(f"WROTE_ANNOTATIONS_CSV: {ANNOTATIONS_CSV_PATH}")
    print(f"ANNOTATION_COUNT: {len(annotations)}")


if __name__ == "__main__":
    main()
