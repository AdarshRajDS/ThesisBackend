from fastapi import APIRouter, UploadFile, File
from app.schemas.pipeline import IngestionResponse
from app.services.ingestion_service import upload_pdf

router = APIRouter(prefix="/upload-pdf", tags=["Ingestion"])


@router.post("/", response_model=IngestionResponse)
def upload(file: UploadFile = File(...)):
    result = upload_pdf(file)

    return IngestionResponse(
        status=result.get("status", "success"),
        message=result.get("message", ""),
        pipeline=result.get("pipeline", []),
        text_ingestion=result.get("text_ingestion"),
        image_extraction=result.get("image_extraction"),
    )