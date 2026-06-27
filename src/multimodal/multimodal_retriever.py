from langchain_chroma import Chroma
from src.config.settings import settings
from src.multimodal.clip_embedding import CLIPEmbedding


class MultimodalRetriever:

    def __init__(self):

        print("DEBUG: Initializing MultimodalRetriever")

        self.embedding = CLIPEmbedding()
        self.vectorstore = Chroma(
            collection_name="multimodal_rag",
            persist_directory=f"{settings.processed_data_dir}/multimodal_chroma"
        )

    def retrieve(self, query, k=20):

        print("\n==============================")
        print("DEBUG RETRIEVER QUERY:", query)
        print("==============================")

        # -----------------------------------------
        # STEP 1 — Embed query using CLIP text encoder
        # -----------------------------------------

        query_embedding = self.embedding.embed_text([query])[0]

        # -----------------------------------------
        # STEP 2 — Query vector database
        # -----------------------------------------

        results = self.vectorstore._collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        print("DEBUG retrieved docs:", len(documents))

        # -----------------------------------------
        # STEP 3 — Separate text and images
        # -----------------------------------------

        text_docs = []
        image_metas = []

        # Chroma distances are 0 = identical, 1 = very different.
        # Similarity = 1 - distance.
        BASE_SIMILARITY_THRESHOLD = 0.10

        all_image_candidates = []

        for doc, meta, dist in zip(documents, metadatas, distances):

            # Convert distance to similarity in [0, 1]
            similarity = 1.0 - float(dist) if dist is not None else 0.0

            if meta.get("type") == "image":
                # keep only images here; text handled by separate text retriever
                meta = dict(meta)  # shallow copy in case we want to log score
                meta["base_similarity"] = similarity
                all_image_candidates.append(meta)
            else:
                text_docs.append(doc)

        # Apply an initial similarity cutoff, but never allow "zero images"
        # because that prevents the reranker from selecting anything.
        image_metas = [
            m for m in all_image_candidates if m.get("base_similarity", 0.0) >= BASE_SIMILARITY_THRESHOLD
        ]

        if not image_metas and all_image_candidates:
            # Fallback: keep the top candidates even if scores are low.
            image_metas = sorted(
                all_image_candidates, key=lambda x: x.get("base_similarity", 0.0), reverse=True
            )[:k]

        print("DEBUG text docs:", len(text_docs))
        print("DEBUG image metas after cutoff:", len(image_metas))

        # -----------------------------------------
        # STEP 4 — Return for RAG pipeline
        # -----------------------------------------

        # Return text documents and filtered image metadatas
        return text_docs, image_metas