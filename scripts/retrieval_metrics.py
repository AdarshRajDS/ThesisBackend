#!/usr/bin/env python3
"""Automatic retrieval metrics (P@k, R@k, nDCG@k, MRR, source overlap) for thesis eval."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

DEFAULT_K = 3
# Cosine similarity threshold on MiniLM for binary relevance (question + gold vs passage).
RELEVANCE_THRESHOLD = 0.38
HIGH_RELEVANCE_THRESHOLD = 0.50


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _passage_text(source: dict) -> str:
    src = source.get("source") or ""
    page = source.get("page")
    preview = source.get("chunk_preview") or ""
    return f"{src} page {page}\n{preview}"


def _source_key(source: dict) -> tuple[str, str]:
    return (str(source.get("source") or ""), str(source.get("page") or ""))


def _is_boundary_gold(gold: str) -> bool:
    g = (gold or "").lower()
    return any(x in g for x in ("refuse", "abstain", "not in corpus", "off-topic", "missing corpus"))


def _graded_relevance(sim: float) -> int:
    if sim >= HIGH_RELEVANCE_THRESHOLD:
        return 2
    if sim >= RELEVANCE_THRESHOLD:
        return 1
    return 0


def _dcg(rels: list[int], k: int) -> float:
    total = 0.0
    for i, rel in enumerate(rels[:k], start=1):
        total += (2**rel - 1) / math.log2(i + 1)
    return total


def _ndcg_at_k(rels: list[int], k: int) -> float:
    dcg = _dcg(rels, k)
    ideal = sorted(rels, reverse=True)
    idcg = _dcg(ideal, k)
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def _cosine(a: list[float], b: list[float]) -> float:
    import numpy as np

    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


@dataclass
class PassageScore:
    source: dict
    similarity: float
    binary_relevant: bool
    graded: int


def score_passages(
    embedder: Any,
    *,
    question: str,
    gold: str,
    sources: list[dict],
    category: str = "",
) -> list[PassageScore]:
    if not sources:
        return []

    query_text = f"{question}\nExpected: {gold}" if gold else question

    try:
        q_emb = embedder.embed_query(query_text)
    except Exception:
        return []

    scored: list[PassageScore] = []
    for src in sources:
        text = _passage_text(src)
        try:
            p_emb = embedder.embed_query(text[:2000])
            sim = _cosine(q_emb, p_emb)
        except Exception:
            sim = 0.0
        binary = sim >= RELEVANCE_THRESHOLD
        graded = _graded_relevance(sim)
        scored.append(
            PassageScore(source=src, similarity=sim, binary_relevant=binary, graded=graded)
        )
    return scored


def compute_metrics(
    scored: list[PassageScore],
    *,
    k: int = DEFAULT_K,
    boundary: bool = False,
) -> dict[str, float | int | None]:
    if not scored:
        return {
            "precision_at_k": None,
            "recall_at_k": None,
            "ndcg_at_k": None,
            "mrr": None,
            "source_overlap": None,
            "relevant_in_top_k": 0,
            "total_relevant": 0,
        }

    top_k = scored[:k]
    rel_top = sum(1 for p in top_k if p.binary_relevant)
    total_rel = sum(1 for p in scored if p.binary_relevant)

    precision = rel_top / k
    recall = rel_top / max(1, total_rel)
    ndcg = _ndcg_at_k([p.graded for p in top_k], k)
    mrr = 0.0
    for i, p in enumerate(scored, start=1):
        if p.binary_relevant:
            mrr = 1.0 / i
            break
    relevant_keys = {_source_key(p.source) for p in scored if p.binary_relevant}
    top_keys = {_source_key(p.source) for p in top_k if p.binary_relevant}
    overlap = len(top_keys) / max(1, len(relevant_keys)) if relevant_keys else 0.0

    return {
        "precision_at_k": round(precision, 3),
        "recall_at_k": round(recall, 3),
        "ndcg_at_k": round(ndcg, 3),
        "mrr": round(mrr, 3),
        "source_overlap": round(overlap, 3),
        "relevant_in_top_k": rel_top,
        "total_relevant": total_rel,
    }


def fmt_metric(v: float | None, *, pct: bool = False) -> str:
    if v is None:
        return ""
    if pct:
        return f"{v * 100:.0f}%"
    return f"{v:.2f}"


def macro_average(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)
