"""Multi-tier exportable-catalog suggestions (deterministic, render-safe)."""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any

try:
    from catalog_exportability import (
        AUTO_EXPORT_CONFIDENCE_THRESHOLD,
        build_suggestion_payload,
        filter_exportable_suggestions,
        is_exportable_catalog_entry,
    )
    from catalog_search import (
        desired_side_from_tokens,
        extract_query_tokens,
        label_token_set,
        rank_catalog_items_by_tokens,
    )
    from query_validation import normalize_part_query
except ImportError:
    from anatomy_mcp.catalog_exportability import (
        AUTO_EXPORT_CONFIDENCE_THRESHOLD,
        build_suggestion_payload,
        filter_exportable_suggestions,
        is_exportable_catalog_entry,
    )
    from anatomy_mcp.catalog_search import (
        desired_side_from_tokens,
        extract_query_tokens,
        label_token_set,
        rank_catalog_items_by_tokens,
    )
    from anatomy_mcp.query_validation import normalize_part_query

try:
    from semantic_index import get_semantic_index, semantic_enabled
except ImportError:
    from anatomy_mcp.semantic_index import get_semantic_index, semantic_enabled

# Colloquial / Latin aliases mapped to normalized catalog tokens (not labels).
COLLOQUIAL_SYNONYMS: dict[str, list[str]] = {
    "brainstem": ["brainstem", "brain_stem", "truncus_encephali"],
    "brain_stem": ["brainstem", "brain_stem"],
    "brain": ["brain", "encephalon", "cerebrum"],
    "cerebrum": ["brain", "cerebrum"],
    "gehirn": ["brain", "encephalon", "cerebrum"],
    "liver": ["liver", "hepar"],
    "leber": ["liver", "hepar"],
    "hepar": ["liver", "hepar"],
    "heart": ["heart", "cor"],
    "herz": ["heart", "cor"],
    "cor": ["heart", "cor"],
    "kidney": ["kidney", "renal", "ren"],
    "niere": ["kidney", "renal", "ren"],
    "renal": ["kidney", "renal"],
    "stomach": ["stomach", "gaster"],
    "magen": ["stomach", "gaster"],
    "gaster": ["stomach", "gaster"],
    "tummy": ["stomach", "gaster"],
    "belly": ["stomach", "abdomen"],
    "pancreas": ["pancreas"],
    "pankreas": ["pancreas"],
    "spinal_cord": ["spinal_cord", "medulla_spinalis"],
    "rueckenmark": ["spinal_cord", "medulla_spinalis"],
    "skull": ["skull", "cranium"],
    "schaedel": ["skull", "cranium"],
    "cranium": ["skull", "cranium"],
    "femur": ["femur", "thigh_bone"],
    "oberschenkel": ["femur", "thigh_bone"],
    "thigh": ["femur", "thigh"],
    "hip": ["hip", "hip_bone", "coxal"],
    "huefte": ["hip", "hip_bone", "coxal"],
    "spleen": ["spleen", "lien"],
    "milz": ["spleen", "lien"],
    "lung": ["lung", "pulmonary"],
    "lunge": ["lung", "pulmonary"],
    "lungs": ["lung", "pulmonary"],
    "eye": ["eye", "ocular", "iris"],
    "auge": ["eye", "ocular", "iris"],
    "nebenniere": ["suprarenal", "adrenal"],
    "kniegelenk": ["knee", "knee_joint"],
    "sprunggelenk": ["ankle", "ankle_joint"],
    "incus": ["incus", "incus_l"],
    "amboss": ["incus", "incus_l"],
    "blood_pump": ["heart", "cor"],
}


def _side_penalty(item: dict[str, Any], want_side: str | None) -> int:
    if not want_side:
        return 0
    label_lower = str(item.get("label") or "").lower()
    side = item.get("side")
    if want_side == "left":
        if side == "right" or label_lower.endswith(".r"):
            return 3
        if side == "left" or label_lower.endswith(".l"):
            return -1
    elif want_side == "right":
        if side == "left" or label_lower.endswith(".l"):
            return 3
        if side == "right" or label_lower.endswith(".r"):
            return -1
    return 0


def _fuzzy_ratio(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0
    return SequenceMatcher(None, query, candidate).ratio()


def _entry_search_strings(entry: dict[str, Any]) -> list[str]:
    strings = [
        str(entry.get("normalized") or ""),
        str(entry.get("label") or "").lower().replace(" ", "_").replace(".", "_"),
    ]
    strings.extend(str(term) for term in entry.get("search_terms") or [])
    return [s for s in strings if s]


def rank_catalog_items_by_partial_tokens(
    catalog_items: list[dict[str, Any]],
    normalized_query: str,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Tier 2: at least one content token overlaps (partial match)."""
    query_tokens = extract_query_tokens(normalized_query)
    content_tokens = [t for t in query_tokens if t not in {"left", "right", "l", "r"}]
    if not content_tokens:
        return []

    want_side = desired_side_from_tokens(query_tokens)
    ranked: list[tuple[tuple, dict[str, Any]]] = []

    for item in catalog_items:
        if not is_exportable_catalog_entry(item):
            continue
        ltokens = label_token_set(item)
        matched = [t for t in content_tokens if t in ltokens]
        if not matched:
            continue
        ratio = len(matched) / len(content_tokens)
        if ratio < 0.34:
            continue
        confidence = 0.55 + (0.30 * ratio)
        sort_key = (
            -ratio,
            _side_penalty(item, want_side),
            len(ltokens),
            str(item.get("label") or "").lower(),
        )
        payload = build_suggestion_payload(
            item,
            match_reason="partial_token_overlap",
            confidence=confidence,
            matched_tokens=matched,
        )
        ranked.append((sort_key, payload))

    ranked.sort(key=lambda row: row[0])
    return [payload for _key, payload in ranked[:limit]]


def rank_catalog_items_by_fuzzy(
    catalog_items: list[dict[str, Any]],
    normalized_query: str,
    *,
    limit: int = 8,
    min_ratio: float = 0.62,
) -> list[dict[str, Any]]:
    """Tier 3: edit-distance style fuzzy match on labels and search terms."""
    query_tokens = extract_query_tokens(normalized_query)
    want_side = desired_side_from_tokens(query_tokens)
    content_tokens = [t for t in query_tokens if t not in {"left", "right", "l", "r"}]
    needle = "_".join(content_tokens) if content_tokens else normalized_query
    if len(needle) < 3:
        return []

    ranked: list[tuple[tuple, dict[str, Any]]] = []
    for item in catalog_items:
        if not is_exportable_catalog_entry(item):
            continue
        best_ratio = 0.0
        for candidate in _entry_search_strings(item):
            ratio = _fuzzy_ratio(needle, candidate)
            if len(needle) >= 4 and candidate.startswith(needle[:3]):
                ratio = max(ratio, _fuzzy_ratio(needle, candidate) + 0.05)
            best_ratio = max(best_ratio, ratio)
        if best_ratio < min_ratio:
            continue
        confidence = 0.58 + (0.32 * best_ratio)
        sort_key = (
            -best_ratio,
            _side_penalty(item, want_side),
            str(item.get("label") or "").lower(),
        )
        payload = build_suggestion_payload(
            item,
            match_reason="fuzzy_label",
            confidence=confidence,
        )
        ranked.append((sort_key, payload))

    ranked.sort(key=lambda row: row[0])
    return [payload for _key, payload in ranked[:limit]]


def rank_by_colloquial_synonyms(
    catalog_items: list[dict[str, Any]],
    normalized_query: str,
    synonyms: dict[str, list[str]] | None = None,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Tier 4: expand colloquial terms then match catalog entries."""
    synonym_map = synonyms or COLLOQUIAL_SYNONYMS
    query_tokens = extract_query_tokens(normalized_query)
    expanded: set[str] = set(query_tokens)
    for token in query_tokens:
        for alt in synonym_map.get(token, []):
            expanded.add(normalize_part_query(alt))

    combined: list[dict[str, Any]] = []
    for token in sorted(expanded):
        if len(token) < 3:
            continue
        partial = rank_catalog_items_by_partial_tokens(
            catalog_items,
            token,
            limit=limit,
        )
        for row in partial:
            row = dict(row)
            row["match_reason"] = "synonym"
            row["confidence"] = max(float(row.get("confidence") or 0), 0.88)
            combined.append(row)

        for item in catalog_items:
            if not is_exportable_catalog_entry(item):
                continue
            ltokens = label_token_set(item)
            if token not in ltokens:
                continue
            combined.append(
                build_suggestion_payload(
                    item,
                    match_reason="synonym",
                    confidence=0.88,
                    matched_tokens=[token],
                )
            )

    return filter_exportable_suggestions(combined, limit=limit)


def _top_level_region(entry: dict[str, Any]) -> str | None:
    paths = entry.get("collection_paths") or []
    if paths and isinstance(paths[0], list) and paths[0]:
        return str(paths[0][0])
    parents = entry.get("parent_collections") or []
    if parents:
        return str(parents[0])
    return None


def rank_hierarchy_neighbors(
    catalog_items: list[dict[str, Any]],
    seed_entries: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Tier 5: siblings under the same parent collection."""
    if not seed_entries:
        return []

    parent_sets: list[frozenset[str]] = []
    for seed in seed_entries:
        parents = frozenset(str(p) for p in (seed.get("parent_collections") or []) if p)
        if parents:
            parent_sets.append(parents)

    if not parent_sets:
        return []

    ranked: list[tuple[tuple, dict[str, Any]]] = []
    seed_labels = {str(s.get("label") or "") for s in seed_entries}

    for item in catalog_items:
        if not is_exportable_catalog_entry(item):
            continue
        label = str(item.get("label") or "")
        if label in seed_labels:
            continue
        item_parents = frozenset(str(p) for p in (item.get("parent_collections") or []) if p)
        if not item_parents:
            continue
        overlap = max(len(item_parents & ps) for ps in parent_sets)
        if overlap <= 0:
            continue
        complexity = str(item.get("estimated_complexity") or "medium")
        complexity_rank = {"low": 0, "medium": 1, "high": 2}.get(complexity, 1)
        sort_key = (-overlap, complexity_rank, label.lower())
        payload = build_suggestion_payload(
            item,
            match_reason="hierarchy_neighbor",
            confidence=0.56 + min(0.12, overlap * 0.04),
        )
        ranked.append((sort_key, payload))

    ranked.sort(key=lambda row: row[0])
    return [payload for _key, payload in ranked[:limit]]


def rank_region_siblings(
    catalog_items: list[dict[str, Any]],
    seed_entries: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Tier 6: other exportable entries in the same top-level anatomical system."""
    regions = {_top_level_region(seed) for seed in seed_entries}
    regions.discard(None)
    if not regions:
        return []

    seed_labels = {str(s.get("label") or "") for s in seed_entries}
    ranked: list[tuple[tuple, dict[str, Any]]] = []

    for item in catalog_items:
        if not is_exportable_catalog_entry(item):
            continue
        label = str(item.get("label") or "")
        if label in seed_labels:
            continue
        region = _top_level_region(item)
        if region not in regions:
            continue
        match_type_rank = 0 if item.get("match_type") == "collection" else 1
        sort_key = (match_type_rank, -int(item.get("object_count") or 0), label.lower())
        payload = build_suggestion_payload(
            item,
            match_reason="region_sibling",
            confidence=0.52,
        )
        ranked.append((sort_key, payload))

    ranked.sort(key=lambda row: row[0])
    return [payload for _key, payload in ranked[:limit]]


def _bbox_center(entry: dict[str, Any]) -> tuple[float, float, float] | None:
    bbox = entry.get("bbox")
    if not isinstance(bbox, dict):
        return None
    try:
        mn = bbox.get("min") or bbox.get("min_corner")
        mx = bbox.get("max") or bbox.get("max_corner")
        if isinstance(mn, (list, tuple)) and isinstance(mx, (list, tuple)) and len(mn) >= 3 and len(mx) >= 3:
            return (
                (float(mn[0]) + float(mx[0])) / 2.0,
                (float(mn[1]) + float(mx[1])) / 2.0,
                (float(mn[2]) + float(mx[2])) / 2.0,
            )
    except (TypeError, ValueError):
        return None
    return None


def rank_by_spatial_proximity(
    catalog_items: list[dict[str, Any]],
    seed_entries: list[dict[str, Any]],
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Tier 7 (optional): spatially nearby entries when bbox metadata exists."""
    seed_centers = [_bbox_center(entry) for entry in seed_entries]
    seed_centers = [c for c in seed_centers if c is not None]
    if not seed_centers:
        return []

    seed_labels = {str(s.get("label") or "") for s in seed_entries}
    ranked: list[tuple[float, dict[str, Any]]] = []

    for item in catalog_items:
        if not is_exportable_catalog_entry(item):
            continue
        label = str(item.get("label") or "")
        if label in seed_labels:
            continue
        center = _bbox_center(item)
        if center is None:
            continue
        dist = min(
            math.sqrt(sum((center[i] - sc[i]) ** 2 for i in range(3)))
            for sc in seed_centers
        )
        payload = build_suggestion_payload(
            item,
            match_reason="spatial_nearby",
            confidence=max(0.42, 0.72 - min(dist, 2.0) * 0.08),
        )
        ranked.append((dist, payload))

    ranked.sort(key=lambda row: row[0])
    return [payload for _dist, payload in ranked[:limit]]


def _catalog_item_by_label(catalog_items: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    for item in catalog_items:
        if str(item.get("label") or "") == label:
            return item
    return None


def _token_hits_to_suggestions(
    token_hits: list[dict[str, Any]],
    catalog_items: list[dict[str, Any]],
    *,
    match_reason: str,
    base_confidence: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hit in token_hits:
        entry = _catalog_item_by_label(catalog_items, str(hit.get("label") or ""))
        if entry is None or not is_exportable_catalog_entry(entry):
            continue
        matched = hit.get("matched_tokens") or []
        confidence = base_confidence
        if matched:
            confidence = min(0.94, base_confidence + 0.04 * len(matched))
        out.append(
            build_suggestion_payload(
                entry,
                match_reason=match_reason,
                confidence=confidence,
                matched_tokens=list(matched),
            )
        )
    return out


def rank_by_semantic_similarity(
    catalog_items: list[dict[str, Any]],
    query_text: str,
    *,
    limit: int = 8,
    min_score: float = 0.30,
) -> list[dict[str, Any]]:
    """Tier 4.5: embedding (MiniLM) similarity fallback for meaning-based queries.

    Resolves intent when the wording never overlaps the Latin catalog labels
    (e.g. "blood filter" -> kidney). Degrades to an empty list when the semantic
    index or model is unavailable, so lexical tiers remain authoritative.
    Confidence is capped below the exact/synonym tiers so ``filter_exportable_suggestions``
    always prefers a deterministic match for the same label.
    """
    query = (query_text or "").strip()
    if not query or not semantic_enabled():
        return []

    index = get_semantic_index()
    if index is None or not index.available:
        return []

    hits = index.search(query, limit=limit * 3, min_score=min_score)
    out: list[dict[str, Any]] = []
    for hit in hits:
        entry = _catalog_item_by_label(catalog_items, str(hit.get("label") or ""))
        if entry is None or not is_exportable_catalog_entry(entry):
            continue
        score = float(hit.get("score") or 0.0)
        confidence = min(0.86, 0.55 + 0.34 * score)
        out.append(
            build_suggestion_payload(
                entry,
                match_reason="semantic",
                confidence=confidence,
            )
        )
        if len(out) >= limit:
            break
    return out


def rank_suggestions_for_query(
    catalog_items: list[dict[str, Any]],
    normalized_query: str,
    *,
    resolver_status: str | None = None,
    resolver_matches: list[str] | None = None,
    synonyms: dict[str, list[str]] | None = None,
    include_nearby: bool = True,
    limit: int = 8,
    query_text: str | None = None,
) -> list[dict[str, Any]]:
    """
    Run all deterministic tiers and return export-safe ranked suggestions.
    """
    if not normalized_query:
        return []

    combined: list[dict[str, Any]] = []

    # Tier 1: full token overlap (existing search ranker).
    token_hits = rank_catalog_items_by_tokens(catalog_items, normalized_query, limit=limit)
    combined.extend(
        _token_hits_to_suggestions(
            token_hits,
            catalog_items,
            match_reason="token_overlap",
            base_confidence=0.84,
        )
    )

    # Tier 2: partial tokens.
    combined.extend(rank_catalog_items_by_partial_tokens(catalog_items, normalized_query, limit=limit))

    # Tier 3: fuzzy labels.
    combined.extend(rank_catalog_items_by_fuzzy(catalog_items, normalized_query, limit=limit))

    # Tier 4: colloquial / Latin synonyms.
    combined.extend(
        rank_by_colloquial_synonyms(
            catalog_items,
            normalized_query,
            synonyms=synonyms,
            limit=limit,
        )
    )

    # Tier 4.5: semantic (embedding) fallback — only when the lexical tiers are
    # thin, to keep latency low when we already have strong deterministic hits.
    strong_labels = {
        str(row.get("label") or "")
        for row in combined
        if float(row.get("confidence") or 0) >= 0.82
    }
    if len(strong_labels) < limit and semantic_enabled():
        semantic_query = (query_text or "").strip() or normalized_query.replace("_", " ")
        combined.extend(
            rank_by_semantic_similarity(catalog_items, semantic_query, limit=limit)
        )

    seeds: list[dict[str, Any]] = []
    for row in combined[:6]:
        entry = _catalog_item_by_label(catalog_items, str(row.get("label") or ""))
        if entry is not None:
            seeds.append(entry)

    if resolver_matches:
        for label in resolver_matches:
            entry = _catalog_item_by_label(catalog_items, label)
            if entry is not None:
                seeds.append(entry)

    if include_nearby and seeds:
        # Tier 5–7: anatomical neighbors.
        combined.extend(rank_hierarchy_neighbors(catalog_items, seeds, limit=limit))
        combined.extend(rank_region_siblings(catalog_items, seeds, limit=limit))
        combined.extend(rank_by_spatial_proximity(catalog_items, seeds, limit=min(6, limit)))

    # Lateral pairs when query is unsided but both sides exist.
    query_tokens = extract_query_tokens(normalized_query)
    want_side = desired_side_from_tokens(query_tokens)
    if want_side is None:
        content = [t for t in query_tokens if t not in {"left", "right", "l", "r"}]
        if len(content) == 1:
            token = content[0]
            for item in catalog_items:
                if not is_exportable_catalog_entry(item) or not item.get("is_pair_candidate"):
                    continue
                ltokens = label_token_set(item)
                if token not in ltokens:
                    continue
                combined.append(
                    build_suggestion_payload(
                        item,
                        match_reason="lateral_pair",
                        confidence=0.80,
                        matched_tokens=[token],
                    )
                )

    if resolver_status == "ambiguous" and resolver_matches:
        for label in resolver_matches:
            entry = _catalog_item_by_label(catalog_items, label)
            if entry is None or not is_exportable_catalog_entry(entry):
                continue
            combined.insert(
                0,
                build_suggestion_payload(
                    entry,
                    match_reason="ambiguous_match",
                    confidence=0.92,
                ),
            )

    filtered = filter_exportable_suggestions(combined, limit=limit)

    # For lateral organ queries (kidney, lung, …), prefer .l/.r object rows over huge collections.
    content_tokens = extract_query_tokens(normalized_query)
    organ_token = next(
        (t for t in content_tokens if t in {"kidney", "lung", "eye", "femur", "hip"}),
        None,
    )
    if organ_token:
        preferred = [
            row
            for row in filtered
            if row.get("match_type") == "object"
            and organ_token in str(row.get("label") or "").lower().replace(".", "_")
        ]
        if preferred:
            rest = [row for row in filtered if row not in preferred]
            filtered = filter_exportable_suggestions(preferred + rest, limit=limit)

    return filtered


def top_auto_export_candidate(
    suggestions: list[dict[str, Any]],
    *,
    threshold: float = AUTO_EXPORT_CONFIDENCE_THRESHOLD,
) -> dict[str, Any] | None:
    if not suggestions:
        return None
    top = suggestions[0]
    if float(top.get("confidence") or 0) >= threshold and top.get("can_export"):
        return top
    return None


def suggestion_labels(suggestions: list[dict[str, Any]], *, limit: int = 6) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for row in suggestions:
        label = str(row.get("label") or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return labels
