from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

# 🔥 This becomes /data on Hugging Face, and stays local when developing
BASE_DATA_DIR = os.getenv("HF_HOME", ".")


def _resolve_storage_provider() -> str:
    """
    Explicit STORAGE_PROVIDER=minio|supabase wins.
    If unset, use Supabase when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set (common misconfig fix).
    """
    explicit = (os.getenv("STORAGE_PROVIDER") or "").strip().lower()
    if explicit in ("minio", "supabase"):
        return explicit
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if url and key:
        return "supabase"
    return "minio"


RESOLVED_STORAGE_PROVIDER = _resolve_storage_provider()


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # 📂 Data paths
    base_data_dir: str = BASE_DATA_DIR
    raw_data_dir: str = os.path.join(BASE_DATA_DIR, "raw")
    processed_data_dir: str = os.path.join(BASE_DATA_DIR, "processed")
    chroma_dir: str = os.path.join(BASE_DATA_DIR, "chroma")

    # 🤖 Models
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = os.getenv("LLM_PROVIDER", "lmstudio")
    llm_model: str = os.getenv("LLM_MODEL", "google/gemma-4-e2b")
    llm_allow_online: bool = os.getenv("LLM_ALLOW_ONLINE", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # 📦 Storage provider (minio or supabase)
    storage_provider: str = RESOLVED_STORAGE_PROVIDER

    # 📦 MinIO (object storage for images in production)
    minio_enabled: bool = os.getenv("MINIO_ENABLED", "true").lower() in ("true", "1", "yes")
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "anatomy-images")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")
    minio_presign_expire_seconds: int = int(os.getenv("MINIO_PRESIGN_EXPIRE", "3600"))

    # 📦 Supabase Storage (object storage alternative)
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase_bucket: str = os.getenv("SUPABASE_BUCKET", "anatomy-images")
    supabase_signed_url_expire_seconds: int = int(os.getenv("SUPABASE_SIGNED_URL_EXPIRE", "3600"))

    blender_server_url: str = os.getenv("BLENDER_SERVER_URL", "")
    blender_output_dir: str = os.getenv("BLENDER_OUTPUT_DIR", os.path.join(BASE_DATA_DIR, "outputs", "blender"))

    # LLM (local LM Studio only by default; see LLM_ALLOW_ONLINE)
    llm_api_base: str = os.getenv("LLM_API_BASE", "http://127.0.0.1:1234/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "lm-studio")

    # Anatomy MCP (3D export)
    anatomy_mcp_enabled: bool = os.getenv("ANATOMY_MCP_ENABLED", "true").lower() in ("true", "1", "yes")
    # Strict MCP agent: when False (default), every /anatomy/ask request goes through the
    # LLM tool-calling loop (the LLM decides the MCP tool calls). Set to "true" to re-enable
    # the deterministic catalog fast-path that bypasses the LLM for simple queries.
    anatomy_mcp_fast_path_enabled: bool = os.getenv(
        "ANATOMY_MCP_FAST_PATH_ENABLED", "false"
    ).lower() in ("true", "1", "yes")
    public_api_base: str = os.getenv(
        "PUBLIC_API_BASE",
        os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000"),
    )
    blender_bin: str = os.getenv("BLENDER_BIN", "")
    z_anatomy_blend: str = os.getenv("Z_ANATOMY_BLEND", "")


settings = Settings()




