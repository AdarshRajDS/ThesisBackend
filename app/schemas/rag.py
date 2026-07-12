from pydantic import BaseModel
from typing import List, Literal, Optional


class AskRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    """Attribution for a text chunk from the PDF / text index."""

    source: Optional[str] = None
    page: Optional[int] = None
    chunk_preview: Optional[str] = None


class AnswerGrounding(BaseModel):
    """
    Heuristic metadata about how the answer was conditioned.
    Does not automatically detect verbatim quotes vs paraphrase (that would need extra NLP or model behavior constraints).
    """

    had_retrieved_passages_in_prompt: bool
    unique_text_passages_used: int
    used_multimodal_text_excerpts: bool
    primary_basis: Literal["retrieved_corpus_synthesized", "general_knowledge_fallback"]
    provenance_explanation: str
    evaluation_note: str


class AskResponse(BaseModel):
    answer: str
    images: Optional[List[str]] = None
    sources: Optional[List[SourceItem]] = None
    grounding: Optional[AnswerGrounding] = None
    render_3d_url: Optional[str] = None
    render_3d_model_url: Optional[str] = None
    render_3d_viewer_url: Optional[str] = None
    render_3d_annotations_url: Optional[str] = None
    render_3d_anatomy: Optional[str] = None
    render_3d_suggestions: Optional[List[str]] = None
