from langchain_chroma import Chroma
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreFactory:

    @staticmethod
    def create(embedding_function):

        persist_dir = f"{settings.processed_data_dir}/chroma"

        logger.info("Loading Chroma vector store...")

        vectordb = Chroma(
            collection_name="multimodal_rag",
            embedding_function=embedding_function,
            persist_directory=persist_dir
        )

        logger.info("Chroma vector store ready.")

        return vectordb
