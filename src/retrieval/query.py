from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():

    logger.info("Starting retrieval query interface...")

    embedding = get_text_embedding()

    vectordb = VectorStoreFactory.create(embedding)

    retriever = vectordb.as_retriever(search_kwargs={"k": 5})

    while True:

        query = input("\nEnter your question (or type 'exit'): ")

        if query.lower() == "exit":
            break

        results = retriever.invoke(query)
        docs = retriever.invoke(query)

        print("\nRETRIEVED CHUNKS:\n")
        for d in docs:
            print(d.page_content[:300])
            print("------")


        print("\nTop retrieved chunks:\n")

        for i, doc in enumerate(results, 1):
            print(f"Result {i}")
            print("-" * 80)
            print(doc.page_content[:500])
            print("\nMETADATA:", doc.metadata)
            print("\n")


if __name__ == "__main__":
    main()
