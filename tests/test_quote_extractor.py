from src.rag.quote_extractor import extract_best_quote, format_quote_answer


def test_exact_quote_found():
    passage = (
        "The lower motor neuron connects to a muscle through a neuromuscular junction "
        "to cause contraction of the target muscle. This is essential for movement."
    )
    result = extract_best_quote(
        [("[1] page 10", passage)],
        "Quote neuromuscular junction definition",
    )
    assert result.found_exact
    answer = format_quote_answer(result)
    assert answer.startswith('"')


def test_no_quote_abstains():
    result = extract_best_quote(
        [("[1] page 1", "Short text only.")],
        "Quote the exact definition of quantum physics",
    )
    assert not result.found_exact
    assert "not an exact quote" in result.message.lower()
