"""
Score and rerank retrieved passages before generation and citation display.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from src.rag.content_heuristics import (
    content_type_bonus,
    content_type_penalty,
    infer_content_type,
)


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}


def term_overlap(query: str, passage: str) -> float:
    q_t = _tokenize(query)
    p_t = _tokenize(passage)
    if not q_t or not p_t:
        return 0.0
    return len(q_t & p_t) / len(q_t)


def heading_match(query: str, metadata: dict[str, Any]) -> float:
    heading = (metadata.get("section_heading") or metadata.get("heading") or "").lower()
    if not heading:
        return 0.0
    q_t = _tokenize(query)
    h_t = _tokenize(heading)
    if not q_t or not h_t:
        return 0.0
    return 0.15 * (len(q_t & h_t) / max(len(q_t), 1))


def figure_id_match(query: str, metadata: dict[str, Any], figure_id: str | None) -> float:
    if not figure_id:
        return 0.0
    meta_fig = metadata.get("figure_id") or ""
    body = (metadata.get("chunk_preview") or "") + " " + str(meta_fig)
    if figure_id in body or f"figure {figure_id}".lower() in body.lower():
        return 0.40
    return 0.0


def compute_support_score(
    query: str,
    passage_body: str,
    metadata: dict[str, Any],
    *,
    question_type: str = "simple",
    figure_id: str | None = None,
    semantic_similarity: float = 0.0,
) -> float:
    ctype = infer_content_type(passage_body, metadata)
    score = (
        0.35 * term_overlap(query, passage_body)
        + 0.35 * min(1.0, max(0.0, semantic_similarity))
        + heading_match(query, metadata)
        + content_type_bonus(ctype, question_type)
        + figure_id_match(query, metadata, figure_id)
        - content_type_penalty(ctype)
    )
    if term_overlap(query, passage_body) < 0.05 and ctype == "body":
        score -= 0.20
    return score


def semantic_similarity_cosine(
    query_embedding: np.ndarray,
    passage_embedding: np.ndarray,
) -> float:
    qn = np.linalg.norm(query_embedding)
    pn = np.linalg.norm(passage_embedding)
    if qn == 0 or pn == 0:
        return 0.0
    return float(np.dot(query_embedding, passage_embedding) / (qn * pn))


def rerank_passages(
    query: str,
    docs: list,
    sources: list[dict],
    *,
    question_type: str = "simple",
    figure_id: str | None = None,
    text_embedder=None,
    min_score: float = 0.12,
    max_passages: int = 3,
) -> tuple[list, list[dict], list[float]]:
    """Return (docs, sources, scores) sorted by support_score descending."""
    if not docs:
        return [], [], []

    query_emb = None
    if text_embedder is not None:
        try:
            query_emb = np.array(text_embedder.embed_query(query), dtype=float)
        except Exception:
            query_emb = None

    scored: list[tuple[float, int]] = []
    for i, d in enumerate(docs):
        body = (getattr(d, "page_content", None) or "").strip()
        meta = getattr(d, "metadata", None) or {}
        sem = 0.0
        if query_emb is not None and text_embedder is not None:
            try:
                pe = np.array(text_embedder.embed_query(body[:512]), dtype=float)
                sem = semantic_similarity_cosine(query_emb, pe)
            except Exception:
                sem = 0.0
        sc = compute_support_score(
            query,
            body,
            meta,
            question_type=question_type,
            figure_id=figure_id,
            semantic_similarity=sem,
        )
        if sc >= min_score:
            scored.append((sc, i))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        # fallback: keep top by original order
        scored = [(0.1, i) for i in range(min(len(docs), max_passages))]

    out_docs, out_src, out_scores = [], [], []
    for sc, i in scored[:max_passages]:
        out_docs.append(docs[i])
        if i < len(sources):
            src = dict(sources[i])
            src["support_score"] = round(sc, 4)
            out_src.append(src)
        out_scores.append(sc)

    return out_docs, out_src, out_scores
