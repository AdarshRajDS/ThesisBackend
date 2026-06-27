from pydantic import BaseModel
from typing import Any, Dict, Optional, List


class UploadResponse(BaseModel):
    status: str
    message: str
    text_ingestion: Dict[str, Any]
    image_extraction: Dict[str, Any]
    pipeline: Optional[List[Dict[str, Any]]] = None