from src.multimodal.multimodal_rag_chain import MultimodalRAG

# Global singleton (lazy-loaded)
rag = None


def get_rag():
    """
    Returns the active RAG instance.
    Creates it only if it doesn't exist.
    """
    global rag
    if rag is None:
        rag = MultimodalRAG()
    return rag


def reload_rag():
    """
    Rebuild RAG after new ingestion so it loads updated Chroma.
    """
    global rag
    rag = MultimodalRAG()


def run_multimodal_rag(question: str):
    """
    FastAPI entry point.
    """

    rag_instance = get_rag()

    answer, images, sources, grounding = rag_instance.ask(question)

    return {
        "answer": answer,
        "images": images,
        "sources": sources,
        "grounding": grounding,
    }


def main():
    while True:
        query = input("\nAsk: ")

        result = run_multimodal_rag(query)

        print("\nANSWER:\n", result["answer"])

        print("\nIMAGES:")
        for img in result["images"]:
            print(img)

        if result.get("sources"):
            print("\nSOURCES:", len(result["sources"]))

        if result.get("grounding"):
            print("\nGROUNDING:", result["grounding"].get("primary_basis"))


if __name__ == "__main__":
    main()
