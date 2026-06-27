from unittest.mock import MagicMock

from langchain_core.documents import Document

from src.retrieval.hybrid_retriever import HybridRetriever, _extract_phrases


def test_extract_phrases_compound():
    phrases = _extract_phrases("What is the neuromuscular junction?")
    assert "neuromuscular junction" in phrases


def test_phrase_search_finds_doc():
    mock_db = MagicMock()
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.vectordb = mock_db
    retriever.text_embedder = None
    retriever._bm25 = None
    retriever._bm25_docs = [
        Document(page_content="The neuromuscular junction uses acetylcholine."),
        Document(page_content="Unrelated content about weather."),
    ]
    results = retriever._phrase_search("neuromuscular junction", k=5)
    assert len(results) >= 1
    assert "neuromuscular" in results[0][0].page_content.lower()
