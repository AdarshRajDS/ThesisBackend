from src.multimodal.multimodal_indexer import MultimodalIndexer


def run_multimodal_indexing():
    """Call from API after image extraction so RAG uses the new images."""
    indexer = MultimodalIndexer()
    indexer.index_images()


def main():
    run_multimodal_indexing()


if __name__ == "__main__":
    main()
