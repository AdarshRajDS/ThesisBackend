from src.multimodal.multimodal_retriever import MultimodalRetriever


def main():

    retriever = MultimodalRetriever()

    while True:

        query = input("\nEnter query: ")

        docs, metas = retriever.retrieve(query)

        for doc, meta in zip(docs, metas):

            print("\nTEXT:\n", doc[:300])

            if meta["type"] == "image":
                print("🖼 IMAGE:", meta["image_path"])


if __name__ == "__main__":
    main()
