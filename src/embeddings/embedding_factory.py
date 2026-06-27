from langchain_huggingface import HuggingFaceEmbeddings
from src.config.settings import settings


def get_text_embedding():
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model
    )
