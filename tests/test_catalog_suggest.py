"""Tests for exportable-catalog suggestion tiers (Phases 1–5)."""

from __future__ import annotations

import pytest

from anatomy_mcp.catalog_exportability import (
    AUTO_EXPORT_CONFIDENCE_THRESHOLD,
    build_suggestion_payload,
    is_exportable_catalog_entry,
)
from anatomy_mcp.catalog_suggest import (
    rank_by_colloquial_synonyms,
    rank_catalog_items_by_fuzzy,
    rank_catalog_items_by_partial_tokens,
    rank_hierarchy_neighbors,
    rank_region_siblings,
    rank_suggestions_for_query,
    suggestion_labels,
    top_auto_export_candidate,
)


def _entry(
    label: str,
    *,
    match_type: str = "object",
    parents: list[str] | None = None,
    paths: list[list[str]] | None = None,
    side: str | None = None,
    bbox: dict | None = None,
    pair: bool = False,
) -> dict:
    normalized = label.lower().replace(" ", "_").replace(".", "_")
    return {
        "id": f"{match_type}:{label}",
        "label": label,
        "normalized": normalized,
        "match_type": match_type,
        "object_names": [label] if match_type == "object" else [],
        "collection_names": [label] if match_type == "collection" else [],
        "object_count": 1 if match_type == "object" else 12,
        "parent_collections": parents or [],
        "collection_paths": paths or [],
        "search_terms": [normalized],
        "side": side,
        "is_pair_candidate": pair,
        "estimated_complexity": "low",
        "bbox": bbox,
    }


MOCK_CATALOG = [
    _entry("Liver", match_type="collection", parents=["Digestive system"], paths=[["Digestive system", "Liver"]]),
    _entry("Stomach", match_type="collection", parents=["Digestive system"], paths=[["Digestive system", "Stomach"]]),
    _entry("Hepar", match_type="object", parents=["Digestive system", "Liver"]),
    _entry("Heart", match_type="collection", parents=["Cardiovascular system"], paths=[["Cardiovascular system", "Heart"]]),
    _entry("Cor", match_type="object", parents=["Cardiovascular system", "Heart"]),
    _entry("Left kidney", match_type="object", parents=["Urinary system"], side="left", pair=True),
    _entry("Right kidney", match_type="object", parents=["Urinary system"], side="right", pair=True),
    _entry("Femur.l", match_type="object", parents=["Skeletal system"], side="left"),
    _entry("Femur.r", match_type="object", parents=["Skeletal system"], side="right"),
]


def test_is_exportable_catalog_entry_requires_geometry():
    assert is_exportable_catalog_entry(MOCK_CATALOG[0]) is True
    assert is_exportable_catalog_entry({"match_type": "object", "object_count": 0}) is False
    assert is_exportable_catalog_entry({"match_type": "empty", "object_count": 1, "object_names": ["x"]}) is False


def test_build_suggestion_payload_marks_exportable():
    payload = build_suggestion_payload(MOCK_CATALOG[0], match_reason="token_overlap", confidence=0.9)
    assert payload["can_export"] is True
    assert payload["export_probe"] == "catalog_verified"
    assert payload["label"] == "Liver"


def test_fuzzy_match_hepat_to_liver():
    hits = rank_catalog_items_by_fuzzy(MOCK_CATALOG, "hepat", min_ratio=0.55)
    labels = [row["label"] for row in hits]
    assert "Liver" in labels or "Hepar" in labels
    assert all(row["can_export"] for row in hits)


def test_colloquial_synonym_tummy_to_stomach():
    hits = rank_by_colloquial_synonyms(MOCK_CATALOG, "tummy")
    labels = [row["label"] for row in hits]
    assert "Stomach" in labels


def test_partial_token_left_femur():
    hits = rank_catalog_items_by_partial_tokens(MOCK_CATALOG, "left_femur")
    labels = [row["label"] for row in hits]
    assert "Femur.l" in labels


def test_hierarchy_neighbors_digestive():
    seeds = [MOCK_CATALOG[0]]  # Liver
    neighbors = rank_hierarchy_neighbors(MOCK_CATALOG, seeds)
    labels = [row["label"] for row in neighbors]
    assert "Stomach" in labels
    assert all(row["match_reason"] == "hierarchy_neighbor" for row in neighbors)


def test_region_siblings_same_system():
    seeds = [MOCK_CATALOG[0]]
    siblings = rank_region_siblings(MOCK_CATALOG, seeds)
    labels = [row["label"] for row in siblings]
    assert "Stomach" in labels


def test_rank_suggestions_for_query_combines_tiers():
    suggestions = rank_suggestions_for_query(MOCK_CATALOG, "hepar", limit=6)
    labels = suggestion_labels(suggestions)
    assert labels
    assert all(row.get("can_export") for row in suggestions)
    assert all(row.get("export_probe") == "catalog_verified" for row in suggestions)


def test_top_auto_export_candidate_threshold():
    suggestions = rank_suggestions_for_query(MOCK_CATALOG, "heart", limit=4)
    top = top_auto_export_candidate(suggestions, threshold=AUTO_EXPORT_CONFIDENCE_THRESHOLD)
    if top is not None:
        assert float(top["confidence"]) >= AUTO_EXPORT_CONFIDENCE_THRESHOLD


def test_ambiguous_resolver_injects_matches():
    suggestions = rank_suggestions_for_query(
        MOCK_CATALOG,
        "kidney",
        resolver_status="ambiguous",
        resolver_matches=["Left kidney", "Right kidney"],
        limit=6,
    )
    labels = suggestion_labels(suggestions)
    assert "Left kidney" in labels
    assert "Right kidney" in labels


@pytest.mark.skipif(
    not __import__("pathlib").Path("anatomy_mcp/label_index/exportable_catalog.json").exists(),
    reason="Full exportable catalog not present",
)
def test_suggest_tool_against_real_catalog():
    from app.services.anatomy_mcp_service import suggest_exportable_anatomy

    payload = suggest_exportable_anatomy("hepat", limit=5)
    assert payload.get("error") is None
    suggestions = payload.get("suggestions") or []
    assert suggestions
    assert all(row.get("can_export") for row in suggestions)
