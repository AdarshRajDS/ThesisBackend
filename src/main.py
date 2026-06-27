from src.config.settings import settings
from src.utils.logger import get_logger
from src.ingestion.loader import DocumentLoader
from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.llm.llm_factory import get_llm

from app.services.object_storage import (
    is_available,
    get_presigned_url,
)



logger = get_logger(__name__)




def main():
    logger.info("Multimodal RAG system initialized.")
    logger.info(f"Running in environment: {settings.app_env}")

    # 🔎 --- MINIO DEBUG BLOCK START ---
    logger.info("---- MINIO DEBUG START ----")
    logger.info(f"MINIO_ENABLED: {settings.minio_enabled}")
    logger.info(f"MINIO_ENDPOINT: {settings.minio_endpoint}")
    logger.info(f"MINIO_ACCESS_KEY: {settings.minio_access_key}")
    logger.info(f"MINIO_SECRET_KEY: {settings.minio_secret_key}")
    logger.info(f"MINIO_BUCKET: {settings.minio_bucket}")

    try:
        available = is_available()
        logger.info(f"MinIO available: {available}")

        test_key = "anatomy+phys+vol2a-30-60/page_1/anatomy+phys+vol2a-30-60_page_1_img_0.jpeg"
        presigned = get_presigned_url(test_key)

        logger.info(f"Test object key: {test_key}")
        logger.info(f"Presigned URL: {presigned}")

    except Exception as e:
        logger.error(f"MinIO debug error: {e}")

    logger.info("---- MINIO DEBUG END ----")
    # 🔎 --- MINIO DEBUG BLOCK END ---

    loader = DocumentLoader()
    loader.load()

    embedding = get_text_embedding()
    logger.info("Embedding model loaded.")

    vectordb = VectorStoreFactory.create(embedding)

    llm = get_llm()

    logger.info("System setup complete.")


if __name__ == "__main__":
    main()
