from pathlib import Path
from app.services.ingestion_logger import write_ingestion_log
import time

from src.config.settings import settings
from src.ingestion.run import run_ingestion
from src.ingestion.run_image_extraction import run_image_extraction
from src.multimodal.run_multimodal_indexing import run_multimodal_indexing
from src.multimodal.run_multimodal_rag import reload_rag
from app.services.object_storage import storage_debug_snapshot

UPLOAD_DIR = Path(settings.raw_data_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def upload_pdf(file):
    start_time = time.time()
    pipeline = []

    file_path = UPLOAD_DIR / file.filename
    file_bytes = file.file.read()
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    pipeline.append(
        {
            "step": 1,
            "name": "save_pdf_to_raw",
            "ok": True,
            "path": str(file_path),
            "size_bytes": len(file_bytes),
        }
    )

    # Pre-flight storage
    storage_info = storage_debug_snapshot()
    if storage_info.get("using_supabase"):
        preflight_ok = bool(
            storage_info.get("supabase_import_ok")
            and storage_info.get("supabase_client_ok")
            and storage_info.get("bucket_exists_in_project") is True
        )
    else:
        preflight_ok = True

    pipeline.append(
        {
            "step": 2,
            "name": "storage_preflight",
            "ok": preflight_ok,
            "detail": storage_info,
        }
    )

    # Only process the uploaded file so existing corpus chunks are not duplicated.
    pdf_names = [file.filename]

    text_result = run_ingestion(pdf_names=pdf_names)
    pipeline.append(
        {
            "step": 3,
            "name": "text_ingestion",
            "ok": text_result.get("status") != "error"
            if isinstance(text_result, dict)
            else True,
            "detail": text_result,
        }
    )

    image_result = run_image_extraction(pdf_names=pdf_names)
    stats = (image_result or {}).get("extractor_stats") or {}

    uploads_ok = stats.get("uploads_ok", 0)
    uploads_failed = stats.get("uploads_failed", 0)
    images_total = stats.get("images_total", 0)

    step4_ok = uploads_failed == 0 and (
        images_total == 0 or uploads_ok > 0
    )

    pipeline.append(
        {
            "step": 4,
            "name": "image_extraction_and_upload",
            "ok": step4_ok,
            "detail": image_result,
        }
    )

    run_multimodal_indexing()
    pipeline.append(
        {
            "step": 5,
            "name": "multimodal_indexing",
            "ok": True,
            "detail": {"note": "see server logs for Chroma indexing"},
        }
    )

    reload_rag()
    pipeline.append(
        {
            "step": 6,
            "name": "rag_reload",
            "ok": True,
            "detail": {"note": "MultimodalRAG singleton refreshed"},
        }
    )

    # ⭐ NEW — runtime metric + persistent ingestion log
    runtime = time.time() - start_time

    pipeline.append(
        {
            "step": 7,
            "name": "total_runtime",
            "ok": True,
            "detail": {"seconds": runtime},
        }
    )

    write_ingestion_log(
        {
            "pdf_name": file.filename,
            "runtime_sec": runtime,
            "images_total": images_total,
            "uploads_failed": uploads_failed,
            "uploads_ok": uploads_ok,
            "text_status": text_result.get("status")
            if isinstance(text_result, dict)
            else "ok",
            "pipeline_steps": pipeline,
        }
    )

    return {
        "status": "success",
        "message": f"{file.filename} ingested and RAG reloaded",
        "text_ingestion": text_result,
        "image_extraction": image_result,
        "pipeline": pipeline,
    }