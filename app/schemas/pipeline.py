from pydantic import BaseModel
from typing import Any, List, Dict, Optional


class PipelineStep(BaseModel):
    step: int
    name: str
    ok: bool
    detail: Optional[Dict[str, Any]] = None


class IngestionResponse(BaseModel):
    status: str
    message: str
    pipeline: List[PipelineStep]
    text_ingestion: Optional[Any] = None
    image_extraction: Optional[Any] = None