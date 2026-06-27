"""
Hybrid retrieval: BM25 + dense vector + phrase matching with RRF fusion.
"""

from __future__ import annotations

import json
import os
import pickle
import re
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

BM25_INDEX_PATH = Path(settings.processed_data_dir) / "bm25_index.pkl"
BM25_META_PATH = Path(settings.processed_data_dir) / "bm25_meta.json"


def _tokenize_for_bm25(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _extract_phrases(query: str) -> list[str]:
    phrases: list[str] = []
    quoted = re.findall(r'"([^"]+)"', query)
    phrases.extend(quoted)
    compounds = [
        "neuromuscular junction",
        "acetylcholine",
        "end plate potential",
        "brain stem",
        "brainstem",
        "action potential",
        "graded potential",
        "gray matter",
        "white matter",
    ]
    lower = query.lower()
    for c in compounds:
        if c in lower:
            phrases.append(c)
    return phrases


class HybridRetriever:
    def __init__(self, vectordb, text_embedder=None):
        self.vectordb = vectordb
        self.text_embedder = text_embedder
        self._bm25: BM25Okapi | None = None
        self._bm25_docs: list[Document] = []
        self._load_or_build_bm25()

    def _load_or_build_bm25(self) -> None:
        if BM25_INDEX_PATH.exists() and BM25_META_PATH.exists():
            try:
                with open(BM25_INDEX_PATH, "rb") as f:
                    data = pickle.load(f)
                self._bm25 = data["bm25"]
                self._bm25_docs = data["docs"]
                logger.info("Loaded BM25 index with %d documents", len(self._bm25_docs))
                return
            except Exception as e:
                logger.warning("BM25 load failed: %s", e)

        self._build_bm25_from_chroma()

    def _build_bm25_from_chroma(self) -> None:
        try:
            coll = self.vectordb._collection
            result = coll.get(include=["documents", "metadatas"])
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
        except Exception as e:
            logger.warning("Could not build BM25 from Chroma: %s", e)
            return

        self._bm25_docs = []
        corpus_tokens: list[list[str]] = []
        for doc_text, meta in zip(documents, metadatas):
            if not doc_text:
                continue
            self._bm25_docs.append(
                Document(page_content=doc_text, metadata=meta or {})
            )
            corpus_tokens.append(_tokenize_for_bm25(doc_text))

        if not corpus_tokens:
            return

        self._bm25 = BM25Okapi(corpus_tokens)
        BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(BM25_INDEX_PATH, "wb") as f:
                pickle.dump({"bm25": self._bm25, "docs": self._bm25_docs}, f)
            with open(BM25_META_PATH, "w", encoding="utf-8") as f:
                json.dump({"count": len(self._bm25_docs)}, f)
            logger.info("Built and saved BM25 index (%d docs)", len(self._bm25_docs))
        except Exception as e:
            logger.warning("BM25 save failed: %s", e)

    def _dense_search(self, query: str, k: int) -> list[tuple[Document, float]]:
        try:
            results = self.vectordb.similarity_search_with_score(query, k=k)
            out = []
            for doc, dist in results:
                # Chroma returns distance; convert to similarity-ish
                sim = 1.0 / (1.0 + float(dist))
                out.append((doc, sim))
            return out
        except Exception:
            docs = self.vectordb.similarity_search(query, k=k)
            return [(d, 0.5) for d in docs]

    def _bm25_search(self, query: str, k: int) -> list[tuple[Document, float]]:
        if not self._bm25 or not self._bm25_docs:
            return []
        tokens = _tokenize_for_bm25(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
        out = []
        max_s = max((s for _, s in ranked), default=1.0) or 1.0
        for idx, sc in ranked:
            if sc <= 0:
                continue
            out.append((self._bm25_docs[idx], float(sc) / max_s))
        return out

    def _phrase_search(self, query: str, k: int) -> list[tuple[Document, float]]:
        phrases = _extract_phrases(query)
        if not phrases or not self._bm25_docs:
            return []
        out: list[tuple[Document, float]] = []
        for doc in self._bm25_docs:
            body_lower = (doc.page_content or "").lower()
            for ph in phrases:
                if ph.lower() in body_lower:
                    out.append((doc, 1.0))
                    break
        return out[:k]

    def search(
        self,
        queries: list[str],
        *,
        k_per_query: int = 24,
        k_final: int = 24,
    ) -> list[Document]:
        """RRF fusion across query variants and retrieval methods."""
        rrf_k = 60
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        def _doc_key(d: Document) -> str:
            meta = d.metadata or {}
            src = meta.get("source") or meta.get("file_path") or ""
            page = meta.get("page", "")
            fp = (d.page_content or "")[:120]
            return f"{src}|{page}|{hash(fp)}"

        def _add_results(results: list[tuple[Document, float]], weight: float = 1.0) -> None:
            for rank, (doc, _) in enumerate(results):
                key = _doc_key(doc)
                doc_map[key] = doc
                scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank + 1)

        for q in queries:
            _add_results(self._dense_search(q, k_per_query), weight=0.5)
            _add_results(self._bm25_search(q, k_per_query), weight=0.4)
            _add_results(self._phrase_search(q, k_per_query), weight=0.1)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k_final]
        return [doc_map[key] for key, _ in ranked]
