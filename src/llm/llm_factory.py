import os

from langchain_openai import ChatOpenAI

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_ONLINE_PROVIDERS = frozenset({"groq", "cloud", "openai", "azure"})


def get_lmstudio_llm(temperature: float = 0.0) -> ChatOpenAI:
    """OpenAI-compatible local server (LM Studio, Ollama, etc.)."""
    logger.info(
        "Loading local LLM at %s: %s (temperature=%s)",
        settings.llm_api_base,
        settings.llm_model,
        temperature,
    )
    return ChatOpenAI(
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key or "lm-studio",
        model=settings.llm_model,
        temperature=temperature,
    )


def _reject_online_provider(provider: str) -> None:
    if provider in _ONLINE_PROVIDERS:
        raise RuntimeError(
            f"Online LLM provider {provider!r} is disabled. "
            "This project is configured for local inference only (LM Studio). "
            "Set LLM_PROVIDER=lmstudio and run a model on http://127.0.0.1:1234/v1."
        )
    if settings.llm_allow_online:
        return
    if provider not in ("lmstudio", "local", "openai_compatible", "ollama"):
        raise ValueError(
            f"Unsupported LLM_PROVIDER={provider!r}. "
            "Use lmstudio, local, openai_compatible, or ollama."
        )


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Production LLM for RAG chat, thesis eval, and other app paths (local only by default)."""
    provider = (settings.llm_provider or "lmstudio").strip().lower()
    _reject_online_provider(provider)
    return get_lmstudio_llm(temperature)
