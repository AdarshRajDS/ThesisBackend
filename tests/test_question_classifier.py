from src.rag.question_classifier import classify_question


def test_quote_classification():
    c = classify_question("Quote the exact sentence about the neuromuscular junction.")
    assert c.question_type == "quote"


def test_figure_classification():
    c = classify_question("What does Figure 12.14 show?")
    assert c.question_type == "multimodal_figure"
    assert c.figure_id == "12.14"


def test_ooc_classification():
    c = classify_question("What is the capital of France?")
    assert c.question_type == "out_of_context"
