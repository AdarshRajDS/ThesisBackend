"""Batch Chroma upserts to stay under the server max batch size."""

from __future__ import annotations

from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Chroma 0.5+ enforces a max batch size (~5k–6k depending on build).
DEFAULT_CHROMA_ADD_BATCH_SIZE = 4000


def add_documents_in_batches(
    vectordb: Any,
    documents: list,
    *,
    batch_size: int = DEFAULT_CHROMA_ADD_BATCH_SIZE,
) -> int:
    """Add LangChain documents to a Chroma vector store in safe-sized batches."""
    total = len(documents)
    if total == 0:
        return 0

    batch_size = max(1, int(batch_size))
    added = 0

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = documents[start:end]
        vectordb.add_documents(batch)
        added += len(batch)
        logger.info(
            "Chroma batch upsert: %s–%s of %s chunks",
            start + 1,
            end,
            total,
        )

    return added
