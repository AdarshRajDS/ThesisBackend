from src.assessment.image_query_retriever import ImageQueryRetriever
from src.assessment.label_extractor import LabelExtractor
from src.assessment.annotation_grader import AnnotationGrader


# 🔥 Global instances for API performance
retriever = ImageQueryRetriever()
extractor = LabelExtractor()
grader = AnnotationGrader()


def run_annotation_grading(image_path: str):
    """
    FastAPI entry point for grading a student annotation.
    """

    reference = retriever.retrieve_similar(image_path)

    user_labels = extractor.extract(image_path)

    result = grader.grade(user_labels, reference)

    return result


def main():
    image_path = input("Enter path to annotated image: ")

    result = run_annotation_grading(image_path)

    print("\nRESULT:\n", result)


if __name__ == "__main__":
    main()
