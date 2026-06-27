import io
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_list_images_empty():
    with patch("app.api.routes.images.os.path.exists", return_value=False):
        response = client.get("/images/all")

    assert response.status_code == 200
    assert response.json() == {"images": []}


@patch("app.api.routes.images.Path.glob", return_value=[Path("brain.png"), Path("brain.JPG")])
@patch("app.api.routes.images.os.path.exists", return_value=True)
def test_list_images_with_files(mock_exists, mock_glob):
    response = client.get("/images/all")

    assert response.status_code == 200
    assert response.json() == {
        "images": ["outputs/brain.png", "outputs/brain.JPG"]
    }
    mock_exists.assert_called_once()
    mock_glob.assert_called_once()


@patch("app.api.routes.rag_experiment.run_thesis_experiment_ask")
def test_rag_experiment_ask(mock_run):
    mock_run.return_value = {
        "question": "What is the hippocampus?",
        "baseline_answer": "General answer.",
        "strict_rag_answer": "From PDF only.",
        "strict_rag_coherent": "Synthesized from PDF.",
        "sources": [],
        "images": [],
        "evaluation": {
            "winner_label": "strict_rag",
            "raw_winner": "A",
            "presentation": {"A": "strict_rag", "B": "baseline"},
        },
        "debug": {"latency_ms": 100, "had_retrieved_passages": True, "num_sources": 0},
        "log_path": None,
    }

    response = client.post(
        "/rag/experiment/ask",
        json={"question": "What is the hippocampus?", "persist_log": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["strict_rag_answer"] == "From PDF only."
    assert body["strict_rag_coherent"] == "Synthesized from PDF."
    assert body["evaluation"]["winner_label"] == "strict_rag"
    mock_run.assert_called_once_with("What is the hippocampus?", persist_log=False)


def test_rag_experiment_gold_template():
    response = client.get("/rag/experiment/gold-template")
    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert response.json()["questions"] == []


@patch("app.api.routes.rag.ask_question")
def test_rag_ask(mock_ask_question):
    mock_ask_question.return_value = {
        "answer": "This is a sample answer.",
        "images": ["outputs/brain.png"],
        "sources": None,
        "grounding": None,
        "render_3d_url": None,
        "render_3d_model_url": None,
        "render_3d_anatomy": None,
    }

    response = client.post("/rag/ask", json={"question": "What is the brain?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "This is a sample answer.",
        "images": ["outputs/brain.png"],
        "sources": None,
        "grounding": None,
        "render_3d_url": None,
        "render_3d_model_url": None,
        "render_3d_anatomy": None,
    }
    mock_ask_question.assert_called_once_with("What is the brain?")


@patch("app.api.routes.visualize.visualize")
def test_visualize(mock_visualize):
    mock_visualize.return_value = {"annotated_image": "outputs/annotated.png"}

    response = client.post("/visualize/", json={"question": "Highlight the hippocampus."})

    assert response.status_code == 200
    assert response.json() == {"annotated_image": "outputs/annotated.png"}
    mock_visualize.assert_called_once_with("Highlight the hippocampus.")


@patch("app.api.routes.grading.grade_annotation")
def test_grade_annotation(mock_grade_annotation):
    mock_grade_annotation.return_value = {
        "score": 0.95,
        "feedback": "Excellent annotation.",
        "missing_structures": [],
    }

    response = client.post(
        "/grade-annotation/",
        files={"file": ("annotation.json", io.BytesIO(b"{}"), "application/json")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "score": 0.95,
        "feedback": "Excellent annotation.",
        "missing_structures": [],
    }
    mock_grade_annotation.assert_called_once()


@patch("app.api.routes.upload.upload_pdf")
def test_upload_pdf(mock_upload_pdf):
    mock_upload_pdf.return_value = {
        "status": "success",
        "message": "PDF uploaded successfully.",
        "pipeline": [],
        "text_ingestion": None,
        "image_extraction": None,
    }

    response = client.post(
        "/upload-pdf/",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4\n"), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "PDF uploaded successfully."
    mock_upload_pdf.assert_called_once()


@patch("app.api.routes.debug_storage.storage_debug_snapshot")
def test_debug_storage(mock_storage_debug_snapshot):
    mock_storage_debug_snapshot.return_value = {
        "storage_provider": "minio",
        "using_supabase": False,
        "minio_enabled": True,
    }

    response = client.get("/debug/storage")

    assert response.status_code == 200
    assert response.json()["storage_provider"] == "minio"
    mock_storage_debug_snapshot.assert_called_once()


@patch("app.api.routes.blender.generate_brain_3d")
def test_generate_brain_3d(mock_generate_brain):
    mock_generate_brain.return_value = {
        "status": "generated",
        "asset_url": "https://supabase.local/brain.glb",
        "preview_url": "https://supabase.local/brain.png",
        "task_id": "brain_test_123",
    }

    response = client.post(
        "/blender/generate-brain-3d",
        json={
            "prompt": "Generate a detailed brain anatomy model.",
            "quality": "standard",
            "format": "glb",
            "include_preview": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "generated"
    assert response.json()["asset_url"] == "https://supabase.local/brain.glb"
    mock_generate_brain.assert_called_once()


@patch("app.api.routes.blender.blender_render_worker_healthcheck")
def test_blender_render_asset_healthcheck(mock_healthcheck):
    mock_healthcheck.return_value = {
        "status": "ok",
        "configured": True,
        "health_url": "http://blender:8001/health",
        "render_asset_url": "http://blender:8001/render-asset",
    }

    response = client.get("/blender/render-asset/healthcheck")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["configured"] is True
    mock_healthcheck.assert_called_once()
