from src.multimodal.thesis_rag_eval import run_thesis_rag_experiment


def run_thesis_experiment_ask(question: str, persist_log: bool = True) -> dict:
    return run_thesis_rag_experiment(question, persist_log=persist_log)


def gold_qa_template() -> dict:
    return {
        "version": 1,
        "questions": [],
    }
