from pydantic import BaseModel
from typing import Optional


class VisualizeRequest(BaseModel):
    question: str


class VisualizeResponse(BaseModel):
    annotated_image: Optional[str]
