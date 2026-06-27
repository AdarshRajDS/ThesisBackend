from unittest.mock import patch

from app.schemas.blender import GenerateBrain3DRequest
from app.services.blender_service import generate_brain_3d


@patch("app.services.blender_service.BlenderMCP.generate_3d_brain")
@patch("app.services.blender_service.get_presigned_url")
@patch("app.services.blender_service.put_object")
def test_generate_brain_3d_uploads_to_storage(mock_put_object, mock_get_presigned_url, mock_generate):
    mock_generate.return_value = {
        "status": "generated",
        "task_id": "brain_test_123",
        "model_path": "/tmp/brain_test_123.glb",
        "preview_path": "/tmp/brain_test_123.png",
    }
    mock_put_object.return_value = True
    mock_get_presigned_url.side_effect = [
        "https://supabase.local/brain_test_123.glb",
        "https://supabase.local/brain_test_123.png",
    ]

    request = GenerateBrain3DRequest(
        prompt="Generate a realistic brain anatomy model.",
        quality="standard",
        format="glb",
        include_preview=True,
    )

    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.read_bytes", return_value=b"dummy"
    ):
        result = generate_brain_3d(request)

    assert result["status"] == "generated"
    assert result["asset_url"] == "https://supabase.local/brain_test_123.glb"
    assert result["preview_url"] == "https://supabase.local/brain_test_123.png"
    assert result["task_id"] == "brain_test_123"
    mock_generate.assert_called_once()
    mock_put_object.assert_called()
    assert mock_get_presigned_url.call_count == 2


def test_generate_brain_3d_rejects_short_prompt():
    request = GenerateBrain3DRequest(
        prompt="brain",
        quality="standard",
        format="glb",
        include_preview=True,
    )

    result = generate_brain_3d(request)

    assert result["status"] == "error"
    assert "Prompt must be at least 10 characters" in result["error"]
