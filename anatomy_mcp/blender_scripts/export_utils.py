import json
from datetime import datetime, timezone

from mathutils import Matrix, Vector


def make_json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if hasattr(value, "to_list"):
        return make_json_safe(value.to_list())
    if hasattr(value, "to_dict"):
        return make_json_safe(value.to_dict())
    return str(value)


def extract_custom_properties(id_block):
    properties = {}
    for key in id_block.keys():
        if key == "_RNA_UI":
            continue
        properties[key] = make_json_safe(id_block[key])
    return properties


def serialize_vector(vector):
    return [round(float(value), 6) for value in vector]


def serialize_matrix(matrix):
    if isinstance(matrix, Matrix):
        rows = matrix
    else:
        rows = Matrix(matrix)
    flattened = []
    for row in rows:
        flattened.extend(round(float(value), 6) for value in row)
    return flattened


def serialize_bound_box(bound_box, matrix_world=None):
    if not bound_box:
        return []

    points = []
    for corner in bound_box:
        point = Vector(corner)
        if matrix_world is not None:
            point = matrix_world @ point
        points.append(serialize_vector(point))
    return points


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat()
