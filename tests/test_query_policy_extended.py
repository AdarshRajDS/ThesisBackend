from src.rag.query_policy import (
    authoritative_external_sources,
    classify_ooc_topic,
)


def test_france_is_general_trivia():
    assert classify_ooc_topic("What is the capital of France?") == "general_trivia"


def test_nice_is_medical_guideline():
    assert classify_ooc_topic("NICE 2024 first-line drug for hypertension") == "medical_guideline"


def test_crispr_authoritative_urls():
    urls = authoritative_external_sources("Explain CRISPR gene editing")
    assert any("genome.gov" in u for u in urls)
    assert not any("wikipedia.org/wiki/Special:Search" in u for u in urls)
