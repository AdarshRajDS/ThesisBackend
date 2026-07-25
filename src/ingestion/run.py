from pathlib import Path

from src.ingestion.chroma_batch import add_documents_in_batches
from src.ingestion.loader import DocumentLoader
from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _invalidate_bm25_cache() -> None:
    """Force HybridRetriever to rebuild BM25 from Chroma after corpus changes."""
    processed = Path(settings.processed_data_dir)
    for name in ("bm25_index.pkl", "bm25_meta.json"):
        path = processed / name
        if path.exists():
            path.unlink()
            logger.info("Removed stale BM25 cache file: %s", path)


def run_ingestion(pdf_names: list[str] | None = None):
    logger.info("Starting ingestion pipeline...")

    loader = DocumentLoader()

    documents = loader.load_pdfs(pdf_names=pdf_names)

    if not documents:
        logger.warning("No documents to ingest.")
        return {"status": "warning", "message": "No documents found"}

    chunks = loader.split_documents(documents)
    logger.info("Prepared %s chunks for Chroma upsert", len(chunks))

    embedding = get_text_embedding()

    vectordb = VectorStoreFactory.create(embedding)

    # Chroma enforces a max upsert batch (~5k–6k); never send one giant batch.
    added = add_documents_in_batches(vectordb, chunks)
    _invalidate_bm25_cache()

    logger.info("Ingestion complete (%s chunks).", added)

    return {
        "status": "success",
        "message": "Text ingestion complete",
        "chunks_added": added,
        "pdf_names": pdf_names,
    }


def main():
    run_ingestion()


if __name__ == "__main__":
    main()
