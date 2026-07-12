"""REST wiring for anatomy suggest/search endpoints."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.api.routes.anatomy_mcp.suggest_exportable_anatomy")
def test_anatomy_suggest_get(mock_suggest):
    mock_suggest.return_value = {
        "status": "suggestions",
        "catalog_query": "hepat",
        "normalized_query": "hepat",
        "catalog_name": "exportable_catalog.json",
        "resolver_status": "not_found",
        "suggestions": [
            {
                "label": "Liver",
                "match_reason": "fuzzy_label",
                "confidence": 0.82,
                "can_export": True,
                "export_probe": "catalog_verified",
            }
        ],
        "suggestion_labels": ["Liver"],
        "auto_export_threshold": 0.95,
    }

    res = client.get("/anatomy/suggest", params={"q": "hepat", "limit": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "suggestions"
    assert body["suggestions"][0]["label"] == "Liver"
    assert body["suggestions"][0]["can_export"] is True
    mock_suggest.assert_called_once()


@patch("app.api.routes.anatomy_mcp.search_anatomy_catalog")
def test_anatomy_search_direct(mock_search):
    mock_search.return_value = {
        "query": "liver",
        "catalog_query": "liver",
        "normalized_query": "liver",
        "catalog_name": "exportable_catalog.json",
        "resolver_status": "ok",
        "result_count": 1,
        "results": [{"label": "Liver", "match_reason": "exact_label"}],
        "suggestions": [],
        "suggestion_labels": [],
    }

    res = client.get("/anatomy/search", params={"q": "liver", "limit": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["result_count"] == 1
    assert body["results"][0]["label"] == "Liver"
