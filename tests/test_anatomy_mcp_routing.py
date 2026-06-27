import asyncio
from unittest.mock import AsyncMock, patch

from app.services.anatomy_mcp_chat import (
    compact_tool_result_for_llm,
    run_lmstudio_mcp_agent,
    sanitize_assistant_answer,
)
from app.services.anatomy_mcp_client import (
    best_catalog_export_match,
    normalize_export_structured,
    structured_to_anatomy_export,
)


@patch("app.services.anatomy_mcp_chat._try_catalog_fast_path", return_value=None)
@patch("app.services.anatomy_mcp_chat.get_mcp_bridge")
@patch("app.services.anatomy_mcp_chat.AsyncOpenAI")
def test_lmstudio_agent_calls_tools_via_bridge(
    mock_openai, mock_get_bridge, _mock_fast_path
):
    bridge = AsyncMock()
    bridge.get_openai_tools = AsyncMock(
        return_value=[
            {
                "type": "function",
                "function": {
                    "name": "export_anatomy_part",
                    "description": "Export part",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
    )
    bridge.call_tool = AsyncMock(
        return_value={
            "structured_content": {
                "model_url": "http://127.0.0.1:8000/anatomy-exports/test.glb",
                "viewer_url": "http://127.0.0.1:8000/anatomy-viewer/index.html",
                "part_label": "Heart",
                "annotation_count": 3,
            }
        }
    )
    mock_get_bridge.return_value = bridge

    tool_call = type(
        "TC",
        (),
        {
            "id": "tc1",
            "function": type(
                "F",
                (),
                {"name": "export_anatomy_part", "arguments": '{"part_query":"heart"}'},
            )(),
        },
    )()

    msg_with_tools = type(
        "M",
        (),
        {"content": None, "tool_calls": [tool_call]},
    )()
    msg_final = type("M", (), {"content": "Exported heart.", "tool_calls": []})()

    completion = type(
        "C",
        (),
        {"choices": [type("Ch", (), {"message": msg_with_tools})()]},
    )()
    completion2 = type(
        "C",
        (),
        {"choices": [type("Ch", (), {"message": msg_final})()]},
    )()

    client = mock_openai.return_value
    client.chat.completions.create = AsyncMock(side_effect=[completion, completion2])

    result = asyncio.run(run_lmstudio_mcp_agent("export the heart"))

    assert "export_anatomy_part" in result["mcp_tools_used"]
    assert result["mcp_tool_steps"][0]["name"] == "export_anatomy_part"
    bridge.call_tool.assert_called()
    assert result["anatomy_export"]["status"] == "ok"
    assert "Exported" in result["answer"]
    assert result["anatomy_export"]["model_url"]


def test_package_export_maps_to_three_urls():
    structured = {
        "part_label": "Brain",
        "viewer_url": "http://127.0.0.1:8000/anatomy-viewer/index.html?model=x",
        "files": {
            "anatomy_glb": "http://127.0.0.1:8000/anatomy-exports/packages/brain/anatomy.glb",
            "annotations_json": "http://127.0.0.1:8000/anatomy-exports/packages/brain/annotations.json",
            "objects_json": "http://127.0.0.1:8000/anatomy-exports/packages/brain/objects.json",
        },
    }
    normalized = normalize_export_structured(structured)
    export = structured_to_anatomy_export(normalized, "brain")
    assert export["status"] == "ok"
    assert export["model_url"].endswith("anatomy.glb")
    assert export["annotations_url"].endswith("annotations.json")


def test_compact_tool_result_omits_metadata_files():
    payload = {
        "structured_content": {
            "part_label": "Brain",
            "viewer_url": "http://127.0.0.1:8000/anatomy-viewer/index.html",
            "files": {"objects_json": "http://127.0.0.1:8000/objects.json"},
        }
    }
    text = compact_tool_result_for_llm(payload)
    assert "objects_json" not in text


def test_best_catalog_export_match_left_femur():
    structured = {
        "normalized_query": "left_femur",
        "results": [
            {
                "label": "Femur.l",
                "match_type": "object",
                "match_reason": "resolved_query",
                "side": "left",
                "id": "object:Femur.l",
            },
            {
                "label": "Head of femur.l",
                "match_type": "object",
                "match_reason": "token_overlap",
                "side": "left",
                "id": "object:Head of femur.l",
            },
        ],
    }
    match = best_catalog_export_match(structured, "left femur")
    assert match is not None
    assert match["label"] == "Femur.l"


def test_sanitize_detects_hallucinated_export_without_tools():
    answer = sanitize_assistant_answer(
        "Exported brain: http://127.0.0.1:8000/anatomy-exports/packages/brain/anatomy.glb",
        tools_used=[],
        language="en",
    )
    assert "without running MCP tools" in answer
