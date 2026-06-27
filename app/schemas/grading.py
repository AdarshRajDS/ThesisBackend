from pydantic import BaseModel
from typing import List, Optional


class GradingResponse(BaseModel):
    score: Optional[float]
    feedback: str
    missing_structures: List[str]
