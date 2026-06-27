import json
import re
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from query_validation import (
    CLARIFICATION_MESSAGE,
    catalog_query_from_user_message,
    is_vague_part_query,
)

# Only one Blender job at a time — parallel exports corrupt each other on Windows.
_BLENDER_EXPORT_LOCK = threading.RLock()

from config import (
    ANNOTATIONS_DIR,
    BLENDER_EXE,
    CACHE_ANNOTATIONS_DIR,
    CACHE_GLB_DIR,
    CACHE_PACKAGES_DIR,
    CACHE_PREVIEW_DIR,
    CACHE_SCHEMA_VERSION,
    BLENDER_EXPORT_TIMEOUT_SECONDS,
    BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS,
    CACHE_DIR,
    EXPORTABLE_CATALOG_PATH,
    EXPORT_LOG_PATH,
    EXPORT_ROOT,
    EXPORT_SCRIPT,
    EXPORT_STUDY_PACKAGE_SCRIPT,
    GLB_DIR,
    LABEL_INDEX_PATH,
    LOGS_DIR,
    MANIFESTS_DIR,
    MAX_QUERY_LENGTH,
    PACKAGES_DIR,
    PREVIEW_DIR,
    PROJECT_ROOT,
    PUBLIC_BASE_URL,
    PUBLIC_VIEWER_URL,
    SCENE_SCAN_DIR,
    Z_ANATOMY_BLEND,
)


SYNONYMS = {
    "brainstem": ["brainstem", "brain_stem", "truncus_encephali"],
    "brain stem": ["brainstem", "brain_stem", "truncus_encephali"],
    "liver": ["liver", "hepar"],
    "heart": ["heart", "cor"],
    "kidney": ["kidney", "renal", "ren"],
    "left kidney": ["left_kidney", "kidney_left", "left_renal"],
    "right kidney": ["right_kidney", "kidney_right", "right_renal"],
    "stomach": ["stomach", "gaster"],
    "pancreas": ["pancreas"],
    "spinal cord": ["spinal_cord", "medulla_spinalis"],
    "skull": ["skull", "cranium"],
    "femur": ["femur", "thigh_bone"],
    "hip": ["hip", "hip_bone", "coxal"],
    "left hip": ["hip_bone_l", "hip_region_l", "hip_bone.l", "hip_region.l"],
    "right hip": ["hip_bone_r", "hip_region_r", "hip_bone.r", "hip_region.r"],
}

QUERY_PATTERN = re.compile(r"^[A-Za-z0-9 ._-]+$")
NORMALIZE_PATTERN = re.compile(r"[^a-z0-9_]+")
SEPARATOR_PATTERN = re.compile(r"_+")

mcp = FastMCP("Anatomy Blender MCP", json_response=True)


def ensure_runtime_dirs() -> None:
    for directory in (
        GLB_DIR,
        PREVIEW_DIR,
        ANNOTATIONS_DIR,
        SCENE_SCAN_DIR,
        MANIFESTS_DIR,
        PACKAGES_DIR,
        CACHE_DIR,
        CACHE_GLB_DIR,
        CACHE_ANNOTATIONS_DIR,
        CACHE_PREVIEW_DIR,
        CACHE_PACKAGES_DIR,
        LOGS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def validate_user_text(value: str, field_name: str) -> str | None:
    trimmed = value.strip()
    if not trimmed:
        return f"{field_name}_is_required"
    if len(trimmed) > MAX_QUERY_LENGTH:
        return f"{field_name}_too_long"
    if not QUERY_PATTERN.fullmatch(trimmed):
        return f"{field_name}_has_invalid_characters"
    return None


def validate_part_query_specificity(part_query: str) -> dict[str, Any] | None:
    if is_vague_part_query(part_query):
        return error_response(
            "query_too_vague",
            part_query=part_query,
            instruction=CLARIFICATION_MESSAGE,
        )
    return None


def normalize_label(value: str) -> str:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    normalized = NORMALIZE_PATTERN.sub("_", normalized)
    normalized = SEPARATOR_PATTERN.sub("_", normalized).strip("_")
    return normalized


def slugify_part_label(value: str) -> str:
    slug = normalize_label(value)
    return slug or "part"


def load_index() -> dict[str, Any]:
    return json.loads(LABEL_INDEX_PATH.read_text(encoding="utf-8"))


def load_exportable_catalog() -> dict[str, Any] | None:
    if not EXPORTABLE_CATALOG_PATH.exists():
        return None
    return json.loads(EXPORTABLE_CATALOG_PATH.read_text(encoding="utf-8"))


def build_lookup_items(index_data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    object_items = []
    for entry in index_data.get("objects", []):
        object_items.append(
            {
                "name": entry["name"],
                "normalized": normalize_label(entry["name"]),
                "collections": entry.get("collections", []),
                "collections_normalized": [normalize_label(name) for name in entry.get("collections", [])],
            }
        )

    collection_items = []
    for entry in index_data.get("collections", []):
        collection_items.append(
            {
                "name": entry["name"],
                "normalized": normalize_label(entry["name"]),
            }
        )

    return object_items, collection_items


def build_catalog_items(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for entry in catalog_data.get("entries", []):
        label = str(entry.get("label", ""))
        if not label:
            continue
        normalized_label = entry.get("normalized_label") or normalize_label(label)
        search_terms = {
            normalized_label,
            *(normalize_label(term) for term in entry.get("search_terms", [])),
            *(normalize_label(name) for name in entry.get("object_names", [])),
            *(normalize_label(name) for name in entry.get("collection_names", [])),
        }
        items.append(
            {
                **entry,
                "label": label,
                "normalized": normalized_label,
                "search_terms": sorted(term for term in search_terms if term),
            }
        )
    return items


def catalog_match_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    match_type = entry.get("match_type", "object")
    names_key = "object_names" if match_type == "object" else "collection_names"
    names = entry.get(names_key) or []
    if not names:
        names = [entry["label"]]
    return {
        "match_type": match_type,
        "label": entry["label"],
        "names": names,
        "collections": entry.get("parent_collections", []),
        "catalog_id": entry.get("id"),
        "object_count": entry.get("object_count", 0),
        "estimated_complexity": entry.get("estimated_complexity"),
        "side": entry.get("side"),
        "is_pair_candidate": bool(entry.get("is_pair_candidate")),
    }


def dedupe_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {}
    for match in matches:
        key = (match["match_type"], tuple(match["names"]))
        unique[key] = match
    return list(unique.values())


def apply_region_hint(matches: list[dict[str, Any]], region_hint: str | None) -> list[dict[str, Any]]:
    if not region_hint or len(matches) <= 1:
        return matches

    hint = normalize_label(region_hint)
    narrowed = []
    for match in matches:
        haystacks = [normalize_label(match["label"])]
        haystacks.extend(normalize_label(name) for name in match["names"])
        if match["match_type"] == "object":
            haystacks.extend(normalize_label(name) for name in match.get("collections", []))
        if any(hint in item for item in haystacks):
            narrowed.append(match)

    return narrowed or matches


def finalize_resolver_output(
    matches: list[dict[str, Any]],
    part_query: str,
    region_hint: str | None = None,
) -> dict[str, Any]:
    matches = dedupe_matches(matches)
    matches = apply_region_hint(matches, region_hint)

    if not matches:
        return {"status": "not_found", "part_query": part_query}

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "part_query": part_query,
            "matches": [match["label"] for match in matches],
        }

    match = matches[0]
    result = {
        "status": "ok",
        "match_type": match["match_type"],
        "part_label": match["label"],
    }
    if match["match_type"] == "object":
        result["object_names"] = match["names"]
    else:
        result["collection_names"] = match["names"]
    for optional_key in ("catalog_id", "object_count", "estimated_complexity", "side", "is_pair_candidate"):
        if optional_key in match:
            result[optional_key] = match[optional_key]
    return result


def resolve_part_query_from_catalog(part_query: str, region_hint: str | None = None) -> dict[str, Any]:
    catalog_data = load_exportable_catalog()
    if catalog_data is None:
        return {"status": "catalog_missing", "part_query": part_query}

    catalog_items = build_catalog_items(catalog_data)
    normalized_query = normalize_label(part_query)

    exact_object_matches = [
        catalog_match_from_entry(item)
        for item in catalog_items
        if item["match_type"] == "object" and item["normalized"] == normalized_query
    ]
    if exact_object_matches:
        return finalize_resolver_output(exact_object_matches, part_query, region_hint)

    exact_collection_matches = [
        catalog_match_from_entry(item)
        for item in catalog_items
        if item["match_type"] == "collection" and item["normalized"] == normalized_query
    ]
    if exact_collection_matches:
        return finalize_resolver_output(exact_collection_matches, part_query, region_hint)

    lateral_matches = []
    if normalized_query.startswith("left_"):
        lateral_base = normalized_query.removeprefix("left_")
        lateral_names = {f"left_{lateral_base}", f"{lateral_base}_l"}
    elif normalized_query.startswith("right_"):
        lateral_base = normalized_query.removeprefix("right_")
        lateral_names = {f"right_{lateral_base}", f"{lateral_base}_r"}
    elif normalized_query.endswith("_left"):
        lateral_base = normalized_query.removesuffix("_left")
        lateral_names = {f"left_{lateral_base}", f"{lateral_base}_l"}
    elif normalized_query.endswith("_right"):
        lateral_base = normalized_query.removesuffix("_right")
        lateral_names = {f"right_{lateral_base}", f"{lateral_base}_r"}
    else:
        lateral_base = normalized_query
        lateral_names = {
            f"left_{lateral_base}",
            f"right_{lateral_base}",
            f"{lateral_base}_l",
            f"{lateral_base}_r",
        }

    if lateral_base:
        for item in catalog_items:
            normalized = item["normalized"]
            if normalized in lateral_names:
                lateral_matches.append(catalog_match_from_entry(item))
    if lateral_matches:
        return finalize_resolver_output(lateral_matches, part_query, region_hint)

    substring_matches = []
    for item in catalog_items:
        haystacks = [item["normalized"], *item.get("search_terms", [])]
        if any(normalized_query and normalized_query in haystack for haystack in haystacks):
            substring_matches.append(catalog_match_from_entry(item))

    if not substring_matches:
        from anatomy_mcp.catalog_search import (
            desired_side_from_tokens,
            extract_query_tokens,
            label_token_set,
        )

        query_tokens = extract_query_tokens(normalized_query)
        content_tokens = [t for t in query_tokens if t not in {"left", "right", "l", "r"}]
        want_side = desired_side_from_tokens(query_tokens)
        if content_tokens:
            for item in catalog_items:
                ltokens = label_token_set(item)
                if not all(token in ltokens for token in content_tokens):
                    continue
                label_lower = str(item.get("label") or "").lower()
                if want_side == "left" and not (
                    item.get("side") == "left" or label_lower.endswith(".l")
                ):
                    continue
                if want_side == "right" and not (
                    item.get("side") == "right" or label_lower.endswith(".r")
                ):
                    continue
                substring_matches.append(catalog_match_from_entry(item))

    if substring_matches:
        return finalize_resolver_output(substring_matches, part_query, region_hint)

    synonym_matches = []
    for synonym in SYNONYMS.get(part_query.lower(), []):
        normalized_synonym = normalize_label(synonym)
        for item in catalog_items:
            if item["normalized"] == normalized_synonym:
                synonym_matches.append(catalog_match_from_entry(item))
    return finalize_resolver_output(synonym_matches, part_query, region_hint)


def resolve_part_query_from_index(part_query: str, region_hint: str | None = None) -> dict[str, Any]:
    index_data = load_index()
    object_items, collection_items = build_lookup_items(index_data)
    normalized_query = normalize_label(part_query)

    exact_object_matches = []
    for item in object_items:
        if item["normalized"] == normalized_query:
            exact_object_matches.append(
                {
                    "match_type": "object",
                    "label": normalize_label(item["name"]),
                    "names": [item["name"]],
                    "collections": item["collections"],
                }
            )
    if exact_object_matches:
        return finalize_resolver_output(exact_object_matches, part_query, region_hint)

    exact_collection_matches = []
    for item in collection_items:
        if item["normalized"] == normalized_query:
            exact_collection_matches.append(
                {
                    "match_type": "collection",
                    "label": normalize_label(item["name"]),
                    "names": [item["name"]],
                }
            )
    if exact_collection_matches:
        return finalize_resolver_output(exact_collection_matches, part_query, region_hint)

    substring_matches = []
    for item in object_items:
        if normalized_query and normalized_query in item["normalized"]:
            substring_matches.append(
                {
                    "match_type": "object",
                    "label": normalize_label(item["name"]),
                    "names": [item["name"]],
                    "collections": item["collections"],
                }
            )
    for item in collection_items:
        if normalized_query and normalized_query in item["normalized"]:
            substring_matches.append(
                {
                    "match_type": "collection",
                    "label": normalize_label(item["name"]),
                    "names": [item["name"]],
                }
            )
    if substring_matches:
        return finalize_resolver_output(substring_matches, part_query, region_hint)

    synonym_terms = SYNONYMS.get(part_query.lower(), [])
    synonym_matches = []
    for synonym in synonym_terms:
        normalized_synonym = normalize_label(synonym)
        for item in object_items:
            if item["normalized"] == normalized_synonym:
                synonym_matches.append(
                    {
                        "match_type": "object",
                        "label": normalize_label(item["name"]),
                        "names": [item["name"]],
                        "collections": item["collections"],
                    }
                )
        for item in collection_items:
            if item["normalized"] == normalized_synonym:
                synonym_matches.append(
                    {
                        "match_type": "collection",
                        "label": normalize_label(item["name"]),
                        "names": [item["name"]],
                    }
                )

    return finalize_resolver_output(synonym_matches, part_query, region_hint)


def resolve_part_query(part_query: str, region_hint: str | None = None) -> dict[str, Any]:
    catalog_result = resolve_part_query_from_catalog(part_query, region_hint=region_hint)
    if catalog_result["status"] != "catalog_missing":
        catalog_result["resolver_source"] = "exportable_catalog"
        return catalog_result

    index_result = resolve_part_query_from_index(part_query, region_hint=region_hint)
    index_result["resolver_source"] = "raw_index"
    return index_result


def parse_blender_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("no_json_result_found_in_blender_stdout")


def normalize_process_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def parse_blender_timing_events(stdout: Any) -> list[dict[str, Any]]:
    stdout = normalize_process_output(stdout)
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("event") == "timing":
            events.append(payload)
    return events


def load_timing_sidecar(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_server_timing_sidecar(path: Path, stage: str, **extra: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.perf_counter()
    payload = load_timing_sidecar(path) or {
        "current_stage": None,
        "stages": [],
        "server_started_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["current_stage"] = stage
    payload["server_updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["stages"].append(
        {
            "event": "server_timing",
            "stage": stage,
            "server_perf_counter": round(now, 6),
            **extra,
        }
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_within_export_root(path: Path) -> None:
    resolved = path.resolve()
    export_root = EXPORT_ROOT.resolve()
    if export_root not in resolved.parents:
        raise ValueError("output_path_outside_export_root")


def build_public_url(file_path: Path) -> str:
    relative_path = file_path.relative_to(EXPORT_ROOT).as_posix()
    return f"{PUBLIC_BASE_URL}/{relative_path}"


def build_viewer_url(model_path: Path, annotations_path: Path) -> str:
    model_url = quote(build_public_url(model_path), safe="")
    annotations_url = quote(build_public_url(annotations_path), safe="")
    return f"{PUBLIC_VIEWER_URL}?model={model_url}&annotations={annotations_url}"


def cache_key(*parts: Any) -> str:
    return "__".join(normalize_label(str(part)) or "none" for part in parts)


def copy_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def read_cached_package_response(package_dir: Path, part_label: str) -> dict[str, Any] | None:
    manifest_path = package_dir / "package_manifest.json"
    anatomy_path = package_dir / "anatomy.glb"
    original_materials_path = package_dir / "anatomy_original_materials.glb"
    annotations_path = package_dir / "annotations.json"
    timings_path = package_dir / "timings.json"

    if not manifest_path.exists() or not anatomy_path.exists() or not annotations_path.exists():
        return None

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    annotation_payload = json.loads(annotations_path.read_text(encoding="utf-8"))
    annotation_count = len(annotation_payload.get("annotations", []))
    if annotation_count <= 0:
        return None

    timings_payload = load_timing_sidecar(timings_path)
    preview_path = package_dir / "preview.png"

    viewer_model_path = anatomy_path
    return {
        "part_label": part_label,
        "export_id": package_dir.name,
        "model_url": build_public_url(anatomy_path),
        "annotations_url": build_public_url(annotations_path),
        "package_url": build_public_url(package_dir),
        "package_manifest_url": build_public_url(manifest_path),
        "viewer_url": build_viewer_url(viewer_model_path, annotations_path),
        "preview_url": build_public_url(preview_path) if preview_path.exists() else None,
        "source_blend": Z_ANATOMY_BLEND.name,
        "selected_objects": manifest_payload.get("selected_objects", []),
        "selected_collections": manifest_payload.get("selected_collections", []),
        "annotation_count": annotation_count,
        "timings": timings_payload,
        "files": {
            key: (build_public_url(package_dir / relative_path) if relative_path else None)
            for key, relative_path in manifest_payload.get("files", {}).items()
        },
        "cache_hit": True,
    }


def populate_part_cache(
    cache_prefix: str,
    glb_path: Path,
    annotations_path: Path,
    preview_path: Path | None,
    timings_path: Path | None,
) -> tuple[Path, Path, Path | None, Path | None]:
    cached_glb = CACHE_GLB_DIR / f"{cache_prefix}.glb"
    cached_annotations = CACHE_ANNOTATIONS_DIR / f"{cache_prefix}.annotations.json"
    cached_preview = CACHE_PREVIEW_DIR / f"{cache_prefix}.png" if preview_path is not None and preview_path.exists() else None
    cached_timings = CACHE_GLB_DIR / f"{cache_prefix}.timings.json" if timings_path is not None and timings_path.exists() else None

    copy_if_exists(glb_path, cached_glb)
    copy_if_exists(annotations_path, cached_annotations)
    if cached_preview is not None:
        copy_if_exists(preview_path, cached_preview)
    if cached_timings is not None:
        copy_if_exists(timings_path, cached_timings)

    return cached_glb, cached_annotations, cached_preview, cached_timings


def append_log(entry: dict[str, Any]) -> None:
    ensure_runtime_dirs()
    with EXPORT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def error_response(error: str, **extra: Any) -> dict[str, Any]:
    payload = {"error": error}
    payload.update(extra)
    return payload


def _should_force_package_export(resolver_result: dict[str, Any]) -> bool:
    """Route very large catalog matches to package export for stability."""
    complexity = str(resolver_result.get("estimated_complexity") or "").lower()
    object_count = resolver_result.get("object_count") or 0
    try:
        object_count = int(object_count)
    except (TypeError, ValueError):
        object_count = 0

    return complexity in {"very_high"} or object_count >= 180


def validate_export_prerequisites(script_path: Path) -> dict[str, Any] | None:
    if not BLENDER_EXE.exists():
        return error_response("blender_not_found", blender_exe=str(BLENDER_EXE))
    if not Z_ANATOMY_BLEND.exists():
        return error_response("source_blend_not_found", source_blend=str(Z_ANATOMY_BLEND))
    if not script_path.exists():
        return error_response("export_script_not_found", export_script=str(script_path))
    if not LABEL_INDEX_PATH.exists():
        return error_response(
            "index_not_found",
            index_path=str(LABEL_INDEX_PATH),
            instruction="Run the scan_z_anatomy.py Blender command first.",
        )
    return None


@mcp.tool()
def search_anatomy_catalog(query: str, limit: int = 20) -> dict[str, Any]:
    """Search exportable Z-Anatomy entries that are proven to contain geometry."""
    validation_error = validate_user_text(query, "query")
    if validation_error:
        return error_response(validation_error, query=query)

    catalog_query = catalog_query_from_user_message(query)
    vague_error = validate_part_query_specificity(catalog_query)
    if vague_error is not None:
        return vague_error

    catalog_data = load_exportable_catalog()
    if catalog_data is None:
        return error_response(
            "exportable_catalog_not_found",
            catalog_path=str(EXPORTABLE_CATALOG_PATH),
            instruction="Run blender_scripts/build_exportable_catalog.py with Blender first.",
        )

    safe_limit = max(1, min(int(limit or 20), 50))
    normalized_query = normalize_label(catalog_query)
    items = build_catalog_items(catalog_data)
    scored = []
    resolved = resolve_part_query(catalog_query)

    if resolved.get("status") == "ok" and resolved.get("resolver_source") == "exportable_catalog":
        resolved_names = set(resolved.get("object_names") or resolved.get("collection_names") or [])
        resolved_match_type = resolved.get("match_type")
        for item in items:
            if item.get("match_type") != resolved_match_type:
                continue
            item_names = set(item.get("object_names", [])) | set(item.get("collection_names", []))
            if resolved_names and resolved_names.isdisjoint(item_names):
                continue
            scored.append(
                (
                    -1,
                    item.get("object_count", 0),
                    item["label"].lower(),
                    {
                        "label": item["label"],
                        "match_type": item.get("match_type"),
                        "object_count": item.get("object_count", 0),
                        "side": item.get("side"),
                        "estimated_complexity": item.get("estimated_complexity"),
                        "id": item.get("id"),
                        "match_reason": "resolved_query",
                        "parent_collections": item.get("parent_collections", []),
                        "object_names": item.get("object_names", [])[:25],
                        "collection_names": item.get("collection_names", []),
                    },
                )
            )

    for item in items:
        terms = [item["normalized"], *item.get("search_terms", [])]
        if item["normalized"] == normalized_query:
            score = 0
            match_reason = "exact_label"
        elif any(term == normalized_query for term in terms):
            score = 1
            match_reason = "exact_search_term"
        elif any(normalized_query and normalized_query in term for term in terms):
            score = 2
            match_reason = "substring"
        else:
            continue

        scored.append(
            (
                score,
                item.get("object_count", 0),
                item["label"].lower(),
                {
                    "label": item["label"],
                    "match_type": item.get("match_type"),
                    "object_count": item.get("object_count", 0),
                    "side": item.get("side"),
                    "estimated_complexity": item.get("estimated_complexity"),
                    "id": item.get("id"),
                    "match_reason": match_reason,
                    "parent_collections": item.get("parent_collections", []),
                    "object_names": item.get("object_names", [])[:25],
                    "collection_names": item.get("collection_names", []),
                },
            )
        )

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    primary_results = [payload for *_unused, payload in scored[:safe_limit]]

    from anatomy_mcp.catalog_search import (
        merge_search_results,
        rank_catalog_items_by_tokens,
    )

    token_hits = rank_catalog_items_by_tokens(
        items,
        normalized_query,
        limit=safe_limit,
    )
    results = merge_search_results(primary_results, token_hits, limit=safe_limit)

    return {
        "query": query,
        "catalog_query": catalog_query,
        "normalized_query": normalized_query,
        "catalog_name": "exportable_catalog.json",
        "catalog_description": (
            "Geometry-proven Z-Anatomy structures from Startup.blend "
            "(built by build_exportable_catalog.py)"
        ),
        "catalog_path": str(EXPORTABLE_CATALOG_PATH),
        "source_blend": Z_ANATOMY_BLEND.name,
        "resolver_source": "exportable_catalog",
        "resolver_status": resolved.get("status"),
        "result_count": len(results),
        "total_matches": max(len(scored), len(token_hits)),
        "results": results,
    }


def _catalog_suggestions_for_query(
    catalog_query: str,
    *,
    limit: int = 6,
) -> list[str]:
    from anatomy_mcp.catalog_search import rank_catalog_items_by_tokens, suggestion_labels

    catalog_data = load_exportable_catalog()
    if catalog_data is None:
        return []
    items = build_catalog_items(catalog_data)
    normalized = normalize_label(catalog_query)
    return suggestion_labels(
        rank_catalog_items_by_tokens(items, normalized, limit=limit),
        limit=limit,
    )


@mcp.tool()
def export_anatomy_part(
    part_query: str,
    include_preview: bool = False,
    region_hint: str | None = None,
) -> dict[str, Any]:
    """Export a single Z-Anatomy body part as GLB and optional PNG preview."""
    started_at = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()

    validation_error = validate_user_text(part_query, "part_query")
    if validation_error:
        return error_response(validation_error, part_query=part_query)

    catalog_query = catalog_query_from_user_message(part_query)
    vague_error = validate_part_query_specificity(catalog_query)
    if vague_error is not None:
        return vague_error

    if region_hint is not None:
        region_error = validate_user_text(region_hint, "region_hint")
        if region_error:
            return error_response(region_error, region_hint=region_hint)

    prerequisite_error = validate_export_prerequisites(EXPORT_SCRIPT)
    if prerequisite_error is not None:
        return prerequisite_error

    ensure_runtime_dirs()
    normalized_query = normalize_label(catalog_query)
    resolver_result = resolve_part_query(catalog_query, region_hint=region_hint)

    if resolver_result["status"] == "not_found":
        suggestions = _catalog_suggestions_for_query(catalog_query)
        return error_response(
            "part_not_found",
            part_query=part_query,
            catalog_query=catalog_query,
            catalog_name="exportable_catalog.json",
            catalog_path=str(EXPORTABLE_CATALOG_PATH),
            suggestions=suggestions,
        )
    if resolver_result["status"] == "ambiguous":
        matches = resolver_result.get("matches") or []
        return error_response(
            "ambiguous_part",
            part_query=part_query,
            catalog_query=catalog_query,
            catalog_name="exportable_catalog.json",
            catalog_path=str(EXPORTABLE_CATALOG_PATH),
            matches=matches,
            suggestions=matches,
        )

    if _should_force_package_export(resolver_result):
        package_result = export_anatomy_package(
            part_query=part_query,
            region_hint=region_hint,
            include_subparts=True,
            include_original_materials=True,
            include_per_object_glb=False,
            include_preview=include_preview,
        )
        if isinstance(package_result, dict) and package_result.get("error"):
            package_result.setdefault("fallback_from", "export_anatomy_part")
            package_result.setdefault("fallback_reason", "large_structure")
        return package_result

    part_label = resolver_result["part_label"]
    cache_prefix = cache_key(
        CACHE_SCHEMA_VERSION,
        part_label,
        resolver_result["match_type"],
        "preview" if include_preview else "no_preview",
    )
    cached_glb = CACHE_GLB_DIR / f"{cache_prefix}.glb"
    cached_annotations = CACHE_ANNOTATIONS_DIR / f"{cache_prefix}.annotations.json"
    cached_preview = CACHE_PREVIEW_DIR / f"{cache_prefix}.png"
    cached_timings = CACHE_GLB_DIR / f"{cache_prefix}.timings.json"

    if cached_glb.exists() and cached_annotations.exists() and (not include_preview or cached_preview.exists()):
        cached_annotation_payload = json.loads(cached_annotations.read_text(encoding="utf-8"))
        cached_annotation_count = len(cached_annotation_payload.get("annotations", []))
        if cached_annotation_count > 0:
            response = {
                "model_url": build_public_url(cached_glb),
                "annotations_url": build_public_url(cached_annotations),
                "viewer_url": build_viewer_url(cached_glb, cached_annotations),
                "preview_url": build_public_url(cached_preview) if include_preview and cached_preview.exists() else None,
                "part_label": part_label,
                "source_blend": Z_ANATOMY_BLEND.name,
                "selected_objects": [],
                "annotation_labels": [],
                "annotation_count": cached_annotation_count,
                "timings": load_timing_sidecar(cached_timings),
                "cache_hit": True,
            }
            append_log(
                {
                    "timestamp": timestamp,
                    "part_query": part_query,
                    "normalized_query": normalized_query,
                    "region_hint": region_hint,
                    "resolver_result": resolver_result,
                    "status": "cache_hit",
                    "cache_prefix": cache_prefix,
                    "cached_glb_path": str(cached_glb),
                    "cached_annotations_path": str(cached_annotations),
                    "cached_preview_path": str(cached_preview) if include_preview and cached_preview.exists() else None,
                    "cached_timings_path": str(cached_timings) if cached_timings.exists() else None,
                }
            )
            return response

    export_id = f"{slugify_part_label(part_label)}_{uuid.uuid4().hex[:8]}"
    glb_path = GLB_DIR / f"{export_id}.glb"
    annotations_path = ANNOTATIONS_DIR / f"{export_id}.annotations.json"
    preview_path = PREVIEW_DIR / f"{export_id}.png"
    timings_path = GLB_DIR / f"{export_id}.timings.json"

    ensure_within_export_root(glb_path)
    ensure_within_export_root(annotations_path)
    if include_preview:
        ensure_within_export_root(preview_path)

    command = [
        str(BLENDER_EXE),
        "--background",
        "--factory-startup",
        "--python",
        str(EXPORT_SCRIPT),
        "--",
        "--blend-path",
        str(Z_ANATOMY_BLEND),
        "--part-label",
        part_label,
        "--out",
        str(glb_path),
        "--annotations-out",
        str(annotations_path),
    ]

    if resolver_result["match_type"] == "object":
        command.extend(["--object-names", "|".join(resolver_result["object_names"])])
    else:
        command.extend(["--collection-names", "|".join(resolver_result["collection_names"])])

    if include_preview:
        command.extend(["--preview", str(preview_path)])

    process_entry = {
        "timestamp": timestamp,
        "part_query": part_query,
        "normalized_query": normalized_query,
        "region_hint": region_hint,
        "resolver_result": resolver_result,
        "glb_path": str(glb_path),
        "annotations_path": str(annotations_path),
        "preview_path": str(preview_path) if include_preview else None,
        "timings_path": str(timings_path),
        "command": command,
    }
    write_server_timing_sidecar(
        timings_path,
        "server_before_blender_launch",
        part_query=part_query,
        command=command,
    )

    try:
        with _BLENDER_EXPORT_LOCK:
            # FIX: stdin=DEVNULL prevents Blender from inheriting the MCP stdio pipe,
            # which caused a pipe deadlock that blocked the process indefinitely.
            # stderr=STDOUT merges Blender's warning output into stdout so both streams
            # are drained together, preventing a separate stderr buffer deadlock.
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=BLENDER_EXPORT_TIMEOUT_SECONDS,
                check=False,
                cwd=str(PROJECT_ROOT),
            )
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        stdout_text = normalize_process_output(exc.stdout)
        stderr_text = normalize_process_output(exc.stderr)
        append_log(
            {
                **process_entry,
                "status": "timeout",
                "duration_ms": duration_ms,
                "timeout_seconds": BLENDER_EXPORT_TIMEOUT_SECONDS,
                "timing_events": parse_blender_timing_events(stdout_text),
                "timings_sidecar": load_timing_sidecar(timings_path),
                "stdout_tail": stdout_text.splitlines()[-20:],
                "stderr_tail": stderr_text.splitlines()[-20:],
            }
        )
        return error_response(
            "blender_timeout",
            timeout_seconds=BLENDER_EXPORT_TIMEOUT_SECONDS,
            part_query=part_query,
            timing_events=parse_blender_timing_events(stdout_text),
            timings_sidecar=load_timing_sidecar(timings_path),
        )

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    timing_events = parse_blender_timing_events(completed.stdout)
    timings_payload = load_timing_sidecar(timings_path)

    try:
        blender_result = parse_blender_json(completed.stdout)
    except ValueError:
        blender_result = {
            "ok": False,
            "error": "invalid_blender_output",
            "stdout_tail": completed.stdout.splitlines()[-20:],
            "stderr_tail": [],
        }

    if completed.returncode != 0 or not blender_result.get("ok"):
        append_log(
            {
                **process_entry,
                "status": "blender_error",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
                "blender_error": blender_result.get("error"),
                "timing_events": timing_events,
                "timings_sidecar": timings_payload,
            }
        )
        fallback_result = error_response(
            "blender_export_failed",
            part_query=part_query,
            blender_exit_code=completed.returncode,
            blender_result=blender_result,
            timing_events=timing_events,
            timings_sidecar=timings_payload,
        )
        package_result = export_anatomy_package(
            part_query=part_query,
            region_hint=region_hint,
            include_subparts=True,
            include_original_materials=True,
            include_per_object_glb=False,
            include_preview=include_preview,
        )
        if isinstance(package_result, dict) and not package_result.get("error"):
            package_result["fallback_from"] = "export_anatomy_part"
            package_result["fallback_reason"] = "blender_export_failed"
            return package_result
        fallback_result["package_fallback"] = package_result
        return fallback_result

    if not glb_path.exists():
        append_log(
            {
                **process_entry,
                "status": "missing_glb",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
            }
        )
        return error_response("glb_not_created", part_query=part_query, glb_path=str(glb_path))

    if not annotations_path.exists():
        append_log(
            {
                **process_entry,
                "status": "missing_annotations",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
            }
        )
        return error_response(
            "annotations_not_created",
            part_query=part_query,
            annotations_path=str(annotations_path),
        )

    if include_preview and not preview_path.exists():
        append_log(
            {
                **process_entry,
                "status": "missing_preview",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
            }
        )
        return error_response(
            "preview_not_created",
            part_query=part_query,
            preview_path=str(preview_path),
        )

    response = {
        "model_url": build_public_url(glb_path),
        "annotations_url": build_public_url(annotations_path),
        "viewer_url": build_viewer_url(glb_path, annotations_path),
        "preview_url": build_public_url(preview_path) if include_preview else None,
        "part_label": part_label,
        "source_blend": Z_ANATOMY_BLEND.name,
        "selected_objects": blender_result.get("selected_objects", []),
        "annotation_labels": blender_result.get("annotation_labels", []),
        "annotation_count": blender_result.get("annotation_count", 0),
        "timings": blender_result.get("timings") or timings_payload,
    }

    cached_glb, cached_annotations, cached_preview, cached_timings = populate_part_cache(
        cache_prefix,
        glb_path,
        annotations_path,
        preview_path if include_preview else None,
        timings_path,
    )

    append_log(
        {
            **process_entry,
            "status": "ok",
            "duration_ms": duration_ms,
            "blender_exit_code": completed.returncode,
            "selected_objects": response["selected_objects"],
            "annotation_labels": response["annotation_labels"],
            "annotation_count": response["annotation_count"],
            "timing_events": timing_events,
            "timings_sidecar": timings_payload,
            "cache_prefix": cache_prefix,
            "cached_glb_path": str(cached_glb),
            "cached_annotations_path": str(cached_annotations),
            "cached_preview_path": str(cached_preview) if cached_preview is not None else None,
            "cached_timings_path": str(cached_timings) if cached_timings is not None else None,
        }
    )
    return response


@mcp.tool()
def export_anatomy_package(
    part_query: str,
    region_hint: str | None = None,
    include_subparts: bool = True,
    include_original_materials: bool = True,
    include_per_object_glb: bool = False,
    include_preview: bool = False,
) -> dict[str, Any]:
    """Export a study-grade anatomy package with manifest, metadata, annotations, and geometry."""
    started_at = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()

    validation_error = validate_user_text(part_query, "part_query")
    if validation_error:
        return error_response(validation_error, part_query=part_query)

    catalog_query = catalog_query_from_user_message(part_query)
    vague_error = validate_part_query_specificity(catalog_query)
    if vague_error is not None:
        return vague_error

    if region_hint is not None:
        region_error = validate_user_text(region_hint, "region_hint")
        if region_error:
            return error_response(region_error, region_hint=region_hint)

    prerequisite_error = validate_export_prerequisites(EXPORT_STUDY_PACKAGE_SCRIPT)
    if prerequisite_error is not None:
        return prerequisite_error

    ensure_runtime_dirs()
    normalized_query = normalize_label(catalog_query)
    resolver_result = resolve_part_query(catalog_query, region_hint=region_hint)

    if resolver_result["status"] == "not_found":
        suggestions = _catalog_suggestions_for_query(catalog_query)
        return error_response(
            "part_not_found",
            part_query=part_query,
            catalog_query=catalog_query,
            catalog_name="exportable_catalog.json",
            catalog_path=str(EXPORTABLE_CATALOG_PATH),
            suggestions=suggestions,
        )
    if resolver_result["status"] == "ambiguous":
        matches = resolver_result.get("matches") or []
        return error_response(
            "ambiguous_part",
            part_query=part_query,
            catalog_query=catalog_query,
            catalog_name="exportable_catalog.json",
            catalog_path=str(EXPORTABLE_CATALOG_PATH),
            matches=matches,
            suggestions=matches,
        )

    part_label = resolver_result["part_label"]
    package_cache_key = cache_key(
        CACHE_SCHEMA_VERSION,
        part_label,
        resolver_result["match_type"],
        "subparts" if include_subparts else "flat",
        "origmats" if include_original_materials else "nomats",
        "perobj" if include_per_object_glb else "single",
        "preview" if include_preview else "no_preview",
    )
    cached_package_dir = CACHE_PACKAGES_DIR / package_cache_key
    cached_response = read_cached_package_response(cached_package_dir, part_label)
    if cached_response is not None:
        append_log(
            {
                "timestamp": timestamp,
                "part_query": part_query,
                "normalized_query": normalized_query,
                "region_hint": region_hint,
                "resolver_result": resolver_result,
                "status": "cache_hit",
                "cache_package_dir": str(cached_package_dir),
            }
        )
        return cached_response

    export_id = f"{slugify_part_label(part_label)}_{uuid.uuid4().hex[:8]}"
    package_dir = PACKAGES_DIR / export_id
    manifest_path = package_dir / "package_manifest.json"
    anatomy_path = package_dir / "anatomy.glb"
    original_materials_path = package_dir / "anatomy_original_materials.glb"
    annotations_path = package_dir / "annotations.json"
    preview_path = package_dir / "preview.png"
    timings_path = package_dir / "timings.json"

    ensure_within_export_root(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(BLENDER_EXE),
        "--background",
        "--factory-startup",
        "--python",
        str(EXPORT_STUDY_PACKAGE_SCRIPT),
        "--",
        "--blend-path",
        str(Z_ANATOMY_BLEND),
        "--part-label",
        part_label,
        "--out-dir",
        str(package_dir),
        "--include-subparts",
        str(include_subparts).lower(),
        "--include-original-materials",
        str(include_original_materials).lower(),
        "--include-per-object-glb",
        str(include_per_object_glb).lower(),
        "--include-preview",
        str(include_preview).lower(),
        "--query",
        part_query,
        "--match-type",
        resolver_result["match_type"],
    ]

    if resolver_result["match_type"] == "object":
        command.extend(["--object-names", "|".join(resolver_result["object_names"])])
    else:
        command.extend(["--collection-names", "|".join(resolver_result["collection_names"])])

    process_entry = {
        "timestamp": timestamp,
        "part_query": part_query,
        "normalized_query": normalized_query,
        "region_hint": region_hint,
        "resolver_result": resolver_result,
        "package_dir": str(package_dir),
        "manifest_path": str(manifest_path),
        "include_subparts": include_subparts,
        "include_original_materials": include_original_materials,
        "include_per_object_glb": include_per_object_glb,
        "include_preview": include_preview,
        "timings_path": str(timings_path),
        "command": command,
    }
    write_server_timing_sidecar(
        timings_path,
        "server_before_blender_launch",
        part_query=part_query,
        command=command,
    )

    try:
        with _BLENDER_EXPORT_LOCK:
            # FIX: stdin=DEVNULL prevents Blender from inheriting the MCP stdio pipe,
            # which caused a pipe deadlock that blocked the process indefinitely.
            # stderr=STDOUT merges Blender's warning output into stdout so both streams
            # are drained together, preventing a separate stderr buffer deadlock.
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS,
                check=False,
                cwd=str(PROJECT_ROOT),
            )
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        stdout_text = normalize_process_output(exc.stdout)
        stderr_text = normalize_process_output(exc.stderr)
        append_log(
            {
                **process_entry,
                "status": "timeout",
                "duration_ms": duration_ms,
                "timeout_seconds": BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS,
                "timing_events": parse_blender_timing_events(stdout_text),
                "timings_sidecar": load_timing_sidecar(timings_path),
                "stdout_tail": stdout_text.splitlines()[-20:],
                "stderr_tail": stderr_text.splitlines()[-20:],
            }
        )
        return error_response(
            "blender_timeout",
            timeout_seconds=BLENDER_STUDY_PACKAGE_TIMEOUT_SECONDS,
            part_query=part_query,
            timing_events=parse_blender_timing_events(stdout_text),
            timings_sidecar=load_timing_sidecar(timings_path),
        )

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    timing_events = parse_blender_timing_events(completed.stdout)
    timings_payload = load_timing_sidecar(timings_path)

    try:
        blender_result = parse_blender_json(completed.stdout)
    except ValueError:
        blender_result = {
            "ok": False,
            "error": "invalid_blender_output",
            "stdout_tail": completed.stdout.splitlines()[-20:],
            "stderr_tail": [],
        }

    if completed.returncode != 0 or not blender_result.get("ok"):
        append_log(
            {
                **process_entry,
                "status": "blender_error",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
                "blender_error": blender_result.get("error"),
                "timing_events": timing_events,
                "timings_sidecar": timings_payload,
            }
        )
        return error_response(
            "blender_export_failed",
            part_query=part_query,
            blender_exit_code=completed.returncode,
            blender_result=blender_result,
            timing_events=timing_events,
            timings_sidecar=timings_payload,
        )

    if not manifest_path.exists():
        append_log(
            {
                **process_entry,
                "status": "missing_manifest",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
            }
        )
        return error_response(
            "package_manifest_not_created",
            part_query=part_query,
            manifest_path=str(manifest_path),
        )

    if not anatomy_path.exists():
        append_log(
            {
                **process_entry,
                "status": "missing_glb",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
            }
        )
        return error_response("glb_not_created", part_query=part_query, glb_path=str(anatomy_path))

    if not annotations_path.exists():
        append_log(
            {
                **process_entry,
                "status": "missing_annotations",
                "duration_ms": duration_ms,
                "blender_exit_code": completed.returncode,
            }
        )
        return error_response(
            "annotations_not_created",
            part_query=part_query,
            annotations_path=str(annotations_path),
        )

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    viewer_model_path = anatomy_path
    response = {
        "part_label": part_label,
        "export_id": export_id,
        "model_url": build_public_url(anatomy_path),
        "annotations_url": build_public_url(annotations_path),
        "package_url": build_public_url(package_dir),
        "package_manifest_url": build_public_url(manifest_path),
        "viewer_url": build_viewer_url(viewer_model_path, annotations_path),
        "preview_url": build_public_url(preview_path) if include_preview and preview_path.exists() else None,
        "source_blend": Z_ANATOMY_BLEND.name,
        "selected_objects": manifest_payload.get("selected_objects", []),
        "selected_collections": manifest_payload.get("selected_collections", []),
        "annotation_count": blender_result.get("annotation_count", 0),
        "timings": blender_result.get("timings") or timings_payload,
        "files": {
            key: (build_public_url(package_dir / relative_path) if relative_path else None)
            for key, relative_path in manifest_payload.get("files", {}).items()
        },
    }

    copy_tree_if_exists(package_dir, cached_package_dir)

    append_log(
        {
            **process_entry,
            "status": "ok",
            "duration_ms": duration_ms,
            "blender_exit_code": completed.returncode,
            "selected_objects": response["selected_objects"],
            "selected_collections": response["selected_collections"],
            "annotation_count": response["annotation_count"],
            "export_id": export_id,
            "timing_events": timing_events,
            "timings_sidecar": timings_payload,
            "cache_package_dir": str(cached_package_dir),
        }
    )
    return response


if __name__ == "__main__":
    ensure_runtime_dirs()
    mcp.run()
