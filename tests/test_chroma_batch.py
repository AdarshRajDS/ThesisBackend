from unittest.mock import MagicMock

from src.ingestion.chroma_batch import add_documents_in_batches


def test_add_documents_in_batches():
    vectordb = MagicMock()
    docs = [f"chunk-{i}" for i in range(10_000)]

    count = add_documents_in_batches(vectordb, docs, batch_size=4000)

    assert count == 10_000
    assert vectordb.add_documents.call_count == 3
    assert len(vectordb.add_documents.call_args_list[0].args[0]) == 4000
    assert len(vectordb.add_documents.call_args_list[1].args[0]) == 4000
    assert len(vectordb.add_documents.call_args_list[2].args[0]) == 2000
