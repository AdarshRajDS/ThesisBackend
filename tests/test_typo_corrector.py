from src.rag.typo_corrector import correct_query


def test_broinstem_corrected():
    corrected, note = correct_query("wat is broinstem")
    assert "brain" in corrected.lower()
    assert note is not None


def test_thalamous_corrected():
    corrected, _ = correct_query("what is thalamous")
    assert "thalamus" in corrected.lower()
