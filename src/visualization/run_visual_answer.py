from src.multimodal.multimodal_rag_chain import MultimodalRAG
from src.visualization.llm_structure_extractor import StructureExtractor
from src.visualization.image_annotator import ImageAnnotator


# 🔥 Global instances (load once for API performance)
rag = MultimodalRAG()
extractor = StructureExtractor()
annotator = ImageAnnotator()


def run_visual_answer(question: str):
    """
    FastAPI entry point for anatomical visual highlighting.

    Returns:
        {
            "annotated_image": str
        }
    """

    answer, images, _sources, _grounding = rag.ask(question)

    if not images:
        return {
            "annotated_image": None
        }

    structures = extractor.extract(question)

    annotated = annotator.annotate(images[0], structures)

    return {
        "annotated_image": annotated
    }


def main():
    while True:
        query = input("\nAsk: ")

        result = run_visual_answer(query)

        print("\nANNOTATED IMAGE:", result["annotated_image"])


if __name__ == "__main__":
    main()
