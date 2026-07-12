import os
from urllib.parse import urlparse

from langchain_openai import ChatOpenAI

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_ONLINE_PROVIDERS = frozenset({"groq", "cloud", "openai", "azure"})
_LOCAL_LLM_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})


def llm_config_snapshot() -> dict[str, object]:
    """Non-secret LLM settings for health/debug endpoints."""
    return {
        "provider": (settings.llm_provider or "lmstudio").strip().lower(),
        "model": settings.llm_model,
        "api_base": settings.llm_api_base,
        "local_only": not settings.llm_allow_online,
        "online_allowed": settings.llm_allow_online,
    }


def _warn_if_legacy_cloud_env() -> None:
    if os.getenv("GROQ_API_KEY"):
        logger.warning(
            "GROQ_API_KEY is set but ignored. This repo uses local LM Studio only "
            "(LLM_PROVIDER=lmstudio, LLM_API_BASE=%s).",
            settings.llm_api_base,
        )


def _assert_local_api_base(api_base: str) -> None:
    """Reject cloud OpenAI-compatible endpoints unless LLM_ALLOW_ONLINE=true."""
    if settings.llm_allow_online:
        return
    parsed = urlparse((api_base or "").strip())
    host = (parsed.hostname or "").lower()
    if host not in _LOCAL_LLM_HOSTS:
        raise RuntimeError(
            f"LLM_API_BASE must point to a local inference server when "
            f"LLM_ALLOW_ONLINE=false. Got host {host!r} from {api_base!r}. "
            "Start LM Studio and use http://127.0.0.1:1234/v1, or set "
            "LLM_ALLOW_ONLINE=true only if you intentionally use a remote API."
        )


def get_lmstudio_llm(temperature: float = 0.0) -> ChatOpenAI:
    """OpenAI-compatible local server (LM Studio, Ollama, etc.)."""
    _warn_if_legacy_cloud_env()
    _assert_local_api_base(settings.llm_api_base)
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
    _warn_if_legacy_cloud_env()
    provider = (settings.llm_provider or "lmstudio").strip().lower()
    _reject_online_provider(provider)
    return get_lmstudio_llm(temperature)
