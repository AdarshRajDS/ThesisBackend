import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from blender_paths import Z_ANATOMY_INDEX_PATH
from export_utils import extract_custom_properties


OUTPUT_PATH = Z_ANATOMY_INDEX_PATH


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    collections = []
    for collection in sorted(bpy.data.collections, key=lambda item: item.name.lower()):
        collections.append(
            {
                "name": collection.name,
                "objects_count": len(collection.objects),
                "all_objects_count": len(collection.all_objects),
                "custom_properties": extract_custom_properties(collection),
            }
        )

    objects = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name.lower()):
        objects.append(
            {
                "name": obj.name,
                "type": obj.type,
                "collections": sorted(
                    {collection.name for collection in obj.users_collection},
                    key=str.lower,
                ),
                "custom_properties": extract_custom_properties(obj),
            }
        )

    payload = {
        "source_blend": bpy.data.filepath,
        "collection_count": len(collections),
        "object_count": len(objects),
        "collections": collections,
        "objects": objects,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"WROTE_INDEX: {OUTPUT_PATH}")
    print(f"COLLECTION_COUNT: {len(collections)}")
    print(f"OBJECT_COUNT: {len(objects)}")


if __name__ == "__main__":
    main()
