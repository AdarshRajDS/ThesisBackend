'''

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.llm.llm_factory import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def main():

    logger.info("Starting RAG query interface...")

    embedding = get_text_embedding()
    vectordb = VectorStoreFactory.create(embedding)
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})

    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
You are an anatomy tutor.

Answer the question using ONLY the context below.

Context:
{context}

Question:
{question}
""")

    rag_chain = (
        prompt
        | llm
        | StrOutputParser()
    )


    


    while True:

        query = input("\nAsk a question (or type 'exit'): ")

        if query.lower() == "exit":
            break

        # 🔎 STEP 1 — RETRIEVE DOCUMENTS
        docs = retriever.invoke(query)

        # 🧪 DEBUG: SEE WHAT IS RETRIEVED (keep for now)
        print("\nRETRIEVED CHUNKS:\n")
        for d in docs:
            print(d.page_content[:300])
            print("------")

        # 🧠 STEP 2 — PREPARE CONTEXT FOR LLM
        context = "\n\n".join(doc.page_content for doc in docs)

        response = rag_chain.invoke({
            "context": context,
            "question": query
        })

        # 🧾 STEP 3 — PRINT ANSWER
        print("\nANSWER:\n")
        print(response)

        # 📚 STEP 4 — PRINT SOURCES
        print("\nSOURCES:\n")
        for doc in docs:
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "unknown")
            print(f"{source} — page {page}")


if __name__ == "__main__":
    main()
'''


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from chromadb import PersistentClient
from minio import Minio

from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.llm.llm_factory import get_llm
from src.utils.logger import get_logger
from src.config.settings import settings
from src.multimodal.clip_embedding import CLIPEmbedding

logger = get_logger(__name__)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def main():

    logger.info("Starting RAG query interface...")

    # -----------------------------
    # TEXT RETRIEVAL SETUP
    # -----------------------------
    embedding = get_text_embedding()

    vectordb = VectorStoreFactory.create(embedding)

    retriever = vectordb.as_retriever(search_kwargs={"k": 5})

    # -----------------------------
    # LLM SETUP
    # -----------------------------
    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
You are an anatomy tutor.

Answer the question using ONLY the context below.

Context:
{context}

Question:
{question}
""")

    rag_chain = (
        prompt
        | llm
        | StrOutputParser()
    )

    # -----------------------------
    # MULTIMODAL IMAGE RETRIEVAL
    # -----------------------------

    client = PersistentClient(
        path=f"{settings.processed_data_dir}/multimodal_chroma"
    )

    image_collection = client.get_collection("multimodal_rag")

    clip_embedder = CLIPEmbedding()

    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False
    )

    SIMILARITY_THRESHOLD = 0.25

    # -----------------------------
    # QUERY LOOP
    # -----------------------------

    while True:

        query = input("\nAsk a question (or type 'exit'): ")

        if query.lower() == "exit":
            break

        # ---------------------------------
        # STEP 1 — TEXT RETRIEVAL
        # ---------------------------------

        docs = retriever.invoke(query)

        print("\nRETRIEVED CHUNKS:\n")

        for d in docs:
            print(d.page_content[:300])
            print("------")

        context = "\n\n".join(doc.page_content for doc in docs)

        # ---------------------------------
        # STEP 2 — IMAGE RETRIEVAL
        # ---------------------------------

        # CLIP text encoder expects a list of texts
        clip_embedding = clip_embedder.embed_text([query])[0]

        image_results = image_collection.query(
            query_embeddings=[clip_embedding.tolist()],
            n_results=20
        )

        relevant_images = []

        for meta, distance in zip(
            image_results["metadatas"][0],
            image_results["distances"][0]
        ):

            similarity = 1 - distance

            if similarity >= SIMILARITY_THRESHOLD:

                relevant_images.append({
                    "meta": meta,
                    "score": similarity
                })

        # sort images by similarity
        relevant_images.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # keep only top 3
        relevant_images = relevant_images[:3]

        image_urls = []

        for item in relevant_images:

            meta = item["meta"]

            try:

                url = minio_client.presigned_get_object(
                    bucket_name=meta["bucket"],
                    object_name=meta["object_key"]
                )

                image_urls.append(url)

            except Exception as e:
                logger.error(f"Error generating URL: {e}")

        # ---------------------------------
        # STEP 3 — GENERATE ANSWER
        # ---------------------------------

        response = rag_chain.invoke({
            "context": context,
            "question": query
        })

        # ---------------------------------
        # STEP 4 — PRINT ANSWER
        # ---------------------------------

        print("\nANSWER:\n")
        print(response)

        # ---------------------------------
        # STEP 5 — SHOW RELEVANT IMAGES
        # ---------------------------------

        print("\nRELEVANT IMAGES:\n")

        if len(image_urls) == 0:
            print("The resource does not contain any relevant image for this question.")
        else:
            for url in image_urls:
                print(url)

        # ---------------------------------
        # STEP 6 — PRINT SOURCES
        # ---------------------------------

        print("\nSOURCES:\n")

        for doc in docs:
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "unknown")
            print(f"{source} — page {page}")


if __name__ == "__main__":
    main()