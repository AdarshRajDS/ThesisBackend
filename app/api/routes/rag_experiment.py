from fastapi import APIRouter

from app.schemas.thesis_rag import (
    GoldQATemplateResponse,
    ThesisExperimentAskRequest,
    ThesisExperimentAskResponse,
)
from app.services.thesis_rag_service import gold_qa_template, run_thesis_experiment_ask

router = APIRouter(prefix="/rag/experiment", tags=["RAG — thesis experiments"])


@router.post("/ask", response_model=ThesisExperimentAskResponse)
def thesis_experiment_ask(req: ThesisExperimentAskRequest):
    """
    Thesis pipeline only: baseline (no context) + strict RAG + coherent synthesized RAG (same passages,
    synthesis prompt) + blind LLM judge comparing baseline vs strict + same retrieval/images as production.
    Production `POST /rag/ask` is unchanged.
    """
    data = run_thesis_experiment_ask(req.question, persist_log=req.persist_log)
    return ThesisExperimentAskResponse(**data)


@router.get("/gold-template", response_model=GoldQATemplateResponse)
def thesis_gold_template():
    """Empty scaffold for a human-scored gold Q&A set."""
    return GoldQATemplateResponse(**gold_qa_template())
