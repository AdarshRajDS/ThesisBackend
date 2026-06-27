import os
from langchain_groq import ChatGroq
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_groq_llm(temperature: float = 0.0) -> ChatGroq:
    """Groq chat model; use different temperatures for baseline vs strict RAG vs judge."""
    logger.info(f"Loading Groq model: {settings.llm_model} (temperature={temperature})")
    return ChatGroq(
        model=settings.llm_model,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
    )


def get_llm():
    return get_groq_llm(0.0)
