"""Tests for RAG render path with MCP catalog suggestions."""

from __future__ import annotations

from unittest.mock import patch

from app.services.blender_service import render_related_anatomy


@patch("app.services.blender_service._legacy_asset_render")
@patch("app.services.blender_service._try_mcp_catalog_render")
def test_render_related_anatomy_prefers_mcp(mock_mcp, mock_legacy):
    mock_mcp.return_value = {
        "status": "rendered",
        "anatomy_key": "Liver",
        "render_3d_url": "http://example.com/preview.png",
        "render_3d_model_url": "http://example.com/model.glb",
        "render_source": "mcp_exportable_catalog",
    }

    result = render_related_anatomy("What does the liver do?")

    assert result["status"] == "rendered"
    assert result["render_source"] == "mcp_exportable_catalog"
    mock_legacy.assert_not_called()


@patch("app.services.blender_service._legacy_asset_render")
@patch("app.services.blender_service._try_mcp_catalog_render")
def test_render_related_anatomy_falls_back_to_legacy(mock_mcp, mock_legacy):
    mock_mcp.return_value = {
        "status": "skipped",
        "reason": "No high-confidence exportable catalog match.",
        "render_3d_suggestions": ["Liver", "Hepar"],
    }
    mock_legacy.return_value = {
        "status": "rendered",
        "anatomy_key": "heart",
        "render_3d_url": "http://example.com/heart.png",
        "render_source": "legacy_blend_asset",
    }

    result = render_related_anatomy("Tell me about the heart")

    assert result["status"] == "rendered"
    assert result["render_source"] == "legacy_blend_asset"
    mock_legacy.assert_called_once()


@patch("app.services.blender_service._legacy_asset_render")
@patch("app.services.blender_service._try_mcp_catalog_render")
def test_render_related_anatomy_returns_suggestions_when_both_skip(mock_mcp, mock_legacy):
    mock_mcp.return_value = {
        "status": "skipped",
        "render_3d_suggestions": ["Liver", "Stomach"],
    }
    mock_legacy.return_value = {"status": "skipped", "reason": "No mapped anatomy keyword found."}

    result = render_related_anatomy("unknown organ xyz")

    assert result["status"] == "skipped"
    assert result["render_3d_suggestions"] == ["Liver", "Stomach"]
