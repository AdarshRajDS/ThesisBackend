from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.schemas.rag import SourceItem


class ThesisExperimentAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    persist_log: bool = True


class ThesisExperimentAskResponse(BaseModel):
    question: str
    baseline_answer: str
    strict_rag_answer: str
    strict_rag_coherent: str
    sources: List[SourceItem]
    images: List[str]
    evaluation: Dict[str, Any]
    debug: Dict[str, Any]
    log_path: Optional[str] = None


class GoldQATemplateResponse(BaseModel):
    """Starter file for human-scored gold questions (export to CSV/JSON for the thesis)."""

    version: int = 1
    questions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description='Each item: {"id": "", "question": "", "expected": "answerable|abstain|needs_figure", "notes": ""}',
    )
