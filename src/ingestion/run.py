from src.ingestion.loader import DocumentLoader
from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_ingestion():
    logger.info("Starting ingestion pipeline...")

    loader = DocumentLoader()

    documents = loader.load_pdfs()

    if not documents:
        logger.warning("No documents to ingest.")
        return {"status": "warning", "message": "No documents found"}

    chunks = loader.split_documents(documents)

    embedding = get_text_embedding()

    vectordb = VectorStoreFactory.create(embedding)

    vectordb.add_documents(chunks)

    logger.info("Ingestion complete.")

    return {"status": "success", "message": "Text ingestion complete"}


def main():
    run_ingestion()


if __name__ == "__main__":
    main()
