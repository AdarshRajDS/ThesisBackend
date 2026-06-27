"""Token-based ranking for exportable_catalog.json search and suggestions."""

from __future__ import annotations

from typing import Any

from anatomy_mcp.query_validation import NON_SPECIFIC_PART_TERMS

LATERAL_TOKENS = frozenset({"left", "right", "l", "r"})


def extract_query_tokens(normalized_query: str) -> list[str]:
    tokens = [t for t in (normalized_query or "").split("_") if t]
    return [
        t
        for t in tokens
        if t not in NON_SPECIFIC_PART_TERMS and len(t) >= 2
    ]


def label_token_set(item: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    normalized = item.get("normalized") or ""
    if normalized:
        tokens.update(normalized.split("_"))
    for term in item.get("search_terms", []):
        if term:
            tokens.update(str(term).split("_"))
    return {t for t in tokens if t}


def desired_side_from_tokens(query_tokens: list[str]) -> str | None:
    if "left" in query_tokens or "l" in query_tokens:
        return "left"
    if "right" in query_tokens or "r" in query_tokens:
        return "right"
    return None


def rank_catalog_items_by_tokens(
    catalog_items: list[dict[str, Any]],
    normalized_query: str,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Score catalog entries by token overlap (avoids missing multi-word queries like left_hip)."""
    query_tokens = extract_query_tokens(normalized_query)
    if not query_tokens:
        return []

    want_side = desired_side_from_tokens(query_tokens)
    content_tokens = [t for t in query_tokens if t not in LATERAL_TOKENS]
    if not content_tokens:
        content_tokens = list(query_tokens)

    ranked: list[tuple[tuple, str, dict[str, Any]]] = []

    for item in catalog_items:
        ltokens = label_token_set(item)
        if not ltokens:
            continue

        matched = [t for t in content_tokens if t in ltokens]
        if not matched or len(matched) < len(content_tokens):
            continue

        label = str(item.get("label") or "")
        label_lower = label.lower()
        side = item.get("side")
        side_penalty = 0
        if want_side == "left":
            if side == "right" or label_lower.endswith(".r"):
                side_penalty = 3
            elif side == "left" or label_lower.endswith(".l"):
                side_penalty = -1
        elif want_side == "right":
            if side == "left" or label_lower.endswith(".l"):
                side_penalty = 3
            elif side == "right" or label_lower.endswith(".r"):
                side_penalty = -1

        # Prefer more matched tokens, then left-side fit, then simpler labels.
        sort_key = (
            -len(matched),
            side_penalty,
            len(ltokens),
            label_lower,
        )
        payload = {
            "label": label,
            "match_type": item.get("match_type"),
            "object_count": item.get("object_count", 0),
            "side": side,
            "estimated_complexity": item.get("estimated_complexity"),
            "id": item.get("id"),
            "match_reason": "token_overlap",
            "matched_tokens": matched,
            "parent_collections": item.get("parent_collections", []),
            "object_names": (item.get("object_names") or [])[:25],
            "collection_names": item.get("collection_names", []),
        }
        ranked.append((sort_key, label, payload))

    ranked.sort(key=lambda row: row[0])

    if want_side in {"left", "right"}:
        preferred_suffix = ".l" if want_side == "left" else ".r"
        preferred = [row for row in ranked if str(row[1]).lower().endswith(preferred_suffix)]
        other = [row for row in ranked if row not in preferred]
        if preferred:
            ranked = preferred + other

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for _sort_key, label, payload in ranked:
        if label in seen:
            continue
        seen.add(label)
        out.append(payload)
        if len(out) >= limit:
            break
    return out


def merge_search_results(
    primary: list[dict[str, Any]],
    token_hits: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    # Prefer token-based hits when present — they handle multi-word queries better.
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in token_hits + primary:
        label = str(row.get("label") or "")
        if not label or label in seen:
            continue
        seen.add(label)
        merged.append(row)
        if len(merged) >= limit:
            break
    return merged


def suggestion_labels(results: list[dict[str, Any]], *, limit: int = 6) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for row in results:
        label = str(row.get("label") or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return labels
