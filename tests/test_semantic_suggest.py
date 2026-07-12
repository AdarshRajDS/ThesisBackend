"""Tests for the semantic (embedding) fallback tier.

These tests never download or run the MiniLM model — they monkeypatch the
semantic index so behaviour is deterministic and offline-safe. The point is to
verify (a) document construction, (b) graceful degradation when the index is
missing, and (c) that the semantic tier backfills suggestions without
overriding stronger deterministic (exact/synonym) matches.
"""

from __future__ import annotations

import anatomy_mcp.catalog_suggest as catalog_suggest
from anatomy_mcp.catalog_suggest import (
    rank_by_semantic_similarity,
    rank_suggestions_for_query,
    suggestion_labels,
)
from anatomy_mcp.semantic_index import build_entry_document


def _entry(
    label: str,
    *,
    match_type: str = "object",
    parents: list[str] | None = None,
    paths: list[list[str]] | None = None,
    side: str | None = None,
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
        "is_pair_candidate": False,
        "estimated_complexity": "low",
    }


MOCK_CATALOG = [
    _entry("Left kidney", match_type="object", parents=["Urinary system"], side="left"),
    _entry("Right kidney", match_type="object", parents=["Urinary system"], side="right"),
    _entry("Liver", match_type="collection", parents=["Digestive system"], paths=[["Digestive system", "Liver"]]),
    _entry("Larynx", match_type="collection", parents=["Respiratory system"], paths=[["Respiratory system", "Larynx"]]),
]


class _FakeIndex:
    """Stand-in for SemanticCatalogIndex returning scripted scores by label."""

    def __init__(self, scored: list[tuple[str, float]], *, available: bool = True):
        self._scored = scored
        self.available = available

    def search(self, query_text, *, limit=8, min_score=0.30):
        return [
            {"label": label, "match_type": "object", "score": score}
            for label, score in self._scored
            if score >= min_score
        ][:limit]


def test_build_entry_document_humanizes_label_and_side():
    doc = build_entry_document(MOCK_CATALOG[0])
    assert "kidney" in doc.lower()
    assert "left" in doc.lower()
    assert "urinary system" in doc.lower()


def test_build_entry_document_marks_collection_as_region():
    doc = build_entry_document(MOCK_CATALOG[2])
    assert "region" in doc.lower()


def test_semantic_disabled_returns_empty(monkeypatch):
    monkeypatch.setattr(catalog_suggest, "semantic_enabled", lambda: False)
    assert rank_by_semantic_similarity(MOCK_CATALOG, "blood filter") == []


def test_semantic_missing_index_degrades(monkeypatch):
    monkeypatch.setattr(catalog_suggest, "semantic_enabled", lambda: True)
    monkeypatch.setattr(catalog_suggest, "get_semantic_index", lambda: None)
    assert rank_by_semantic_similarity(MOCK_CATALOG, "blood filter") == []


def test_semantic_unavailable_index_degrades(monkeypatch):
    monkeypatch.setattr(catalog_suggest, "semantic_enabled", lambda: True)
    monkeypatch.setattr(
        catalog_suggest,
        "get_semantic_index",
        lambda: _FakeIndex([("Left kidney", 0.7)], available=False),
    )
    assert rank_by_semantic_similarity(MOCK_CATALOG, "blood filter") == []


def test_semantic_maps_scores_to_exportable_suggestions(monkeypatch):
    monkeypatch.setattr(catalog_suggest, "semantic_enabled", lambda: True)
    monkeypatch.setattr(
        catalog_suggest,
        "get_semantic_index",
        lambda: _FakeIndex([("Larynx", 0.62), ("Left kidney", 0.41)]),
    )
    hits = rank_by_semantic_similarity(MOCK_CATALOG, "voice box", limit=5)
    labels = [row["label"] for row in hits]
    assert "Larynx" in labels
    assert all(row["match_reason"] == "semantic" for row in hits)
    assert all(row["can_export"] for row in hits)
    # Confidence stays below the exact/synonym tiers (<= 0.86 cap).
    assert all(row["confidence"] <= 0.86 for row in hits)


def test_semantic_backfills_when_lexical_thin(monkeypatch):
    monkeypatch.setattr(catalog_suggest, "semantic_enabled", lambda: True)
    monkeypatch.setattr(
        catalog_suggest,
        "get_semantic_index",
        lambda: _FakeIndex([("Larynx", 0.60)]),
    )
    # "voice box" has no lexical overlap with any label -> semantic supplies it.
    suggestions = rank_suggestions_for_query(
        MOCK_CATALOG,
        "voice_box",
        query_text="voice box",
        limit=6,
    )
    assert "Larynx" in suggestion_labels(suggestions)


def test_semantic_does_not_override_strong_lexical(monkeypatch):
    # A strong exact lexical hit should keep its higher confidence even if the
    # semantic tier scores the same label lower.
    monkeypatch.setattr(catalog_suggest, "semantic_enabled", lambda: True)
    monkeypatch.setattr(
        catalog_suggest,
        "get_semantic_index",
        lambda: _FakeIndex([("Liver", 0.40)]),
    )
    suggestions = rank_suggestions_for_query(
        MOCK_CATALOG,
        "liver",
        query_text="liver",
        limit=6,
    )
    liver_rows = [r for r in suggestions if r["label"] == "Liver"]
    assert liver_rows
    assert liver_rows[0]["match_reason"] != "semantic"
