import bpy
from pathlib import Path
import sys

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


OUTPUT_DIR = SCENE_SCAN_DIR


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
        return {
            "vertices": 0,
            "edges": 0,
            "polygons": 0,
        }

    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "polygons": len(obj.data.polygons),
    }


def material_texture_paths(material):
    if material.node_tree is None:
        return []

    image_paths = []
    for node in material.node_tree.nodes:
        if getattr(node, "type", None) != "TEX_IMAGE":
            continue
        image = getattr(node, "image", None)
        if image is None:
            continue
        image_paths.append(image.filepath or image.name)

    return sorted(set(image_paths), key=str.lower)


def visible_in_active_view_layer(obj):
    view_layer = bpy.context.view_layer
    try:
        return obj.visible_get(view_layer=view_layer)
    except TypeError:
        return obj.visible_get()


def scan_collections(parent_lookup):
    collections = []
    for collection in sorted(bpy.data.collections, key=lambda item: item.name.lower()):
        collections.append(
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
    return collections


def scan_objects():
    objects = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name.lower()):
        world_matrix = obj.matrix_world.copy()
        objects.append(
            {
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
                "visible_in_view_layer": bool(visible_in_active_view_layer(obj)),
                "bound_box_local": serialize_bound_box(getattr(obj, "bound_box", None)),
                "bound_box_world": serialize_bound_box(getattr(obj, "bound_box", None), world_matrix),
                "mesh_stats": mesh_stats(obj),
            }
        )
    return objects


def scan_materials():
    materials = []
    for material in sorted(bpy.data.materials, key=lambda item: item.name.lower()):
        users = []
        for obj in bpy.data.objects:
            material_names = [slot.material.name for slot in obj.material_slots if slot.material]
            if material.name in material_names:
                users.append(obj.name)

        materials.append(
            {
                "name": material.name,
                "use_nodes": bool(material.node_tree is not None),
                "custom_properties": extract_custom_properties(material),
                "node_types": (
                    sorted((node.bl_idname for node in material.node_tree.nodes), key=str.lower)
                    if material.node_tree is not None
                    else []
                ),
                "image_textures": material_texture_paths(material),
                "users": sorted(users, key=str.lower),
            }
        )
    return materials


def scan_relations(collections, objects):
    return {
        "object_to_collections": {
            item["name"]: item["collections"] for item in objects
        },
        "collection_to_parent": {
            item["name"]: item["parent"] for item in collections
        },
        "parent_to_children_objects": {
            item["name"]: item["children"] for item in objects if item["children"]
        },
    }


def scene_manifest(collections, objects, materials):
    return {
        "source_blend": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "generated_at": utc_timestamp(),
        "collection_count": len(collections),
        "object_count": len(objects),
        "material_count": len(materials),
        "scene_name": bpy.context.scene.name,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parent_lookup = build_collection_parent_lookup()
    collections = scan_collections(parent_lookup)
    objects = scan_objects()
    materials = scan_materials()
    relations = scan_relations(collections, objects)
    manifest = scene_manifest(collections, objects, materials)

    write_json(OUTPUT_DIR / "scene_manifest.json", manifest)
    write_json(OUTPUT_DIR / "collections_full.json", {"collections": collections})
    write_json(OUTPUT_DIR / "objects_full.json", {"objects": objects})
    write_json(OUTPUT_DIR / "materials_full.json", {"materials": materials})
    write_json(OUTPUT_DIR / "relations_full.json", relations)

    print(f"WROTE_SCENE_MANIFEST: {OUTPUT_DIR / 'scene_manifest.json'}")
    print(f"WROTE_COLLECTIONS: {OUTPUT_DIR / 'collections_full.json'}")
    print(f"WROTE_OBJECTS: {OUTPUT_DIR / 'objects_full.json'}")
    print(f"WROTE_MATERIALS: {OUTPUT_DIR / 'materials_full.json'}")
    print(f"WROTE_RELATIONS: {OUTPUT_DIR / 'relations_full.json'}")


if __name__ == "__main__":
    main()
