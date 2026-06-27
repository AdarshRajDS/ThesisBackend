from fastapi import APIRouter
from app.schemas.rag import AskRequest, AskResponse
from app.services.rag_service import ask_question

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    return ask_question(req.question)
