from src.visualization.run_visual_answer import run_visual_answer


def visualize(question: str):

    result = run_visual_answer(question)

    return {
        "annotated_image": result["annotated_image"]
    }
