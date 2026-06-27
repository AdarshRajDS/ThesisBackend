from fastapi import APIRouter, UploadFile, File
from app.schemas.grading import GradingResponse
from app.services.grading_service import grade_annotation

router = APIRouter(prefix="/grade-annotation", tags=["Grading"])


@router.post("/", response_model=GradingResponse)
def grade(file: UploadFile = File(...)):
    return grade_annotation(file)
