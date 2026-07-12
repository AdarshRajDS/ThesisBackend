"""Exportability contract: every suggestion must reference renderable catalog geometry."""

from __future__ import annotations

from typing import Any

EXPORTABLE_MATCH_TYPES = frozenset({"object", "collection"})
EXPORT_PROBE = "catalog_verified"
AUTO_EXPORT_CONFIDENCE_THRESHOLD = 0.95


def is_exportable_catalog_entry(entry: dict[str, Any]) -> bool:
    """True when the catalog entry has proven exportable geometry."""
    if not entry:
        return False
    if entry.get("match_type") not in EXPORTABLE_MATCH_TYPES:
        return False
    if int(entry.get("object_count") or 0) <= 0:
        return False
    object_names = entry.get("object_names") or []
    collection_names = entry.get("collection_names") or []
    return bool(object_names or collection_names)


def build_suggestion_payload(
    entry: dict[str, Any],
    *,
    match_reason: str,
    confidence: float,
    matched_tokens: list[str] | None = None,
) -> dict[str, Any]:
    """Structured suggestion row guaranteed to reference an exportable catalog entry."""
    if not is_exportable_catalog_entry(entry):
        raise ValueError(f"Entry is not exportable: {entry.get('label')}")

    label = str(entry.get("label") or "")
    return {
        "label": label,
        "catalog_id": entry.get("id"),
        "match_type": entry.get("match_type"),
        "object_count": int(entry.get("object_count") or 0),
        "estimated_complexity": entry.get("estimated_complexity"),
        "side": entry.get("side"),
        "match_reason": match_reason,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "can_export": True,
        "export_probe": EXPORT_PROBE,
        "parent_collections": list(entry.get("parent_collections") or [])[:8],
        "collection_paths": list(entry.get("collection_paths") or [])[:4],
        "matched_tokens": matched_tokens or [],
        "is_pair_candidate": bool(entry.get("is_pair_candidate")),
    }


def filter_exportable_suggestions(
    suggestions: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Drop invalid rows and dedupe by label, preserving highest confidence."""
    by_label: dict[str, dict[str, Any]] = {}
    for row in suggestions:
        if not row.get("can_export") or row.get("export_probe") != EXPORT_PROBE:
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        existing = by_label.get(label)
        if existing is None or float(row.get("confidence") or 0) > float(existing.get("confidence") or 0):
            by_label[label] = row

    ranked = sorted(
        by_label.values(),
        key=lambda item: (-float(item.get("confidence") or 0), str(item.get("label") or "").lower()),
    )
    return ranked[:limit]
