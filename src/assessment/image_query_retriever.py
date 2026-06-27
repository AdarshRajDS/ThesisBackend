from src.multimodal.clip_embedding import CLIPEmbedding
from langchain_chroma import Chroma
from src.config.settings import settings


class ImageQueryRetriever:

    def __init__(self):

        self.embedding = CLIPEmbedding()

        self.vectorstore = Chroma(
            collection_name="multimodal_rag",
            persist_directory=f"{settings.processed_data_dir}/multimodal_chroma"
        )

    def retrieve_similar(self, image_path, k=1):

        emb = self.embedding.embed_image([image_path])[0]

        results = self.vectorstore._collection.query(
            query_embeddings=[emb.tolist()],
            n_results=k
        )

        return results["metadatas"][0]
