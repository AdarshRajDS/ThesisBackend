#!/usr/bin/env python3
"""Compute P@3, R@3, nDCG@3, MRR, source overlap for eval JSON runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_eval_section12 import EXCLUDED_IDS, _in_scored_set, load_rag_results
from retrieval_metrics import (
    DEFAULT_K,
    RELEVANCE_THRESHOLD,
    compute_metrics,
    macro_average,
    score_passages,
)

OUTPUT = REPO / "eval" / "retrieval_metrics.json"


def _get_embedder():
    sys.path.insert(0, str(REPO))
    from src.embeddings.embedding_factory import get_text_embedding

    return get_text_embedding()


def _score_row(
    embedder,
    *,
    qid: str,
    question: str,
    gold: str,
    category: str,
    sources: list[dict],
) -> dict:
    boundary = category == "boundary"
    scored = score_passages(
        embedder,
        question=question,
        gold=gold or "",
        sources=sources,
        category=category,
    )
    metrics = compute_metrics(scored, k=DEFAULT_K, boundary=boundary)
    return {
        "id": qid,
        "category": category,
        "boundary": boundary,
        "k": DEFAULT_K,
        "threshold": RELEVANCE_THRESHOLD,
        "num_sources": len(sources),
        "passages": [
            {
                "source": p.source.get("source"),
                "page": p.source.get("page"),
                "similarity": round(p.similarity, 3),
                "relevant": p.binary_relevant,
            }
            for p in scored[:10]
        ],
        **metrics,
    }


def compute_english(embedder) -> list[dict]:
    catalog, results = load_rag_results()
    by_id = {r["id"]: r for r in results}
    rows = []
    for item in catalog:
        qid = item["id"]
        row = by_id.get(qid) or {}
        if not _in_scored_set({**item, **row, "response": row.get("response"), "error": row.get("error")}):
            continue
        resp = row.get("response") or {}
        sources = resp.get("sources") or []
        rows.append(
            _score_row(
                embedder,
                qid=qid,
                question=item["question"],
                gold=item.get("gold") or "",
                category=item.get("category") or "",
                sources=sources,
            )
        )
    return rows


def compute_professor(embedder) -> list[dict]:
    from build_eval_section import PROFESSOR_META

    data = json.loads((REPO / "german_eval_lmstudio_results.json").read_text(encoding="utf-8"))
    rows = []
    for i, (item, (cat, gold)) in enumerate(zip(data, PROFESSOR_META), 1):
        if item.get("error"):
            continue
        resp = item.get("response") or {}
        sources = resp.get("sources") or []
        rows.append(
            _score_row(
                embedder,
                qid=f"LM-R{i:02d}",
                question=item["question"],
                gold=gold,
                category=cat.split("/")[0].strip().lower(),
                sources=sources,
            )
        )
    return rows


def _summarize(rows: list[dict], *, exclude_boundary: bool = True) -> dict:
    pool = [r for r in rows if not (exclude_boundary and r.get("boundary"))]
    keys = ("precision_at_k", "recall_at_k", "ndcg_at_k", "mrr", "source_overlap")
    summary = {"n": len(pool), "k": DEFAULT_K}
    for key in keys:
        summary[key] = macro_average(pool, key)
    return summary


def main() -> None:
    print("Loading embedding model…")
    embedder = _get_embedder()

    english = compute_english(embedder)
    professor = compute_professor(embedder)

    out = {
        "method": (
            "Automatic proxy: cosine similarity (all-MiniLM-L6-v2) between "
            f"question+gold and each ranked passage; binary relevance ≥ {RELEVANCE_THRESHOLD}. "
            "Boundary questions excluded from macro averages."
        ),
        "k": DEFAULT_K,
        "english_rag_55": {
            "rows": english,
        "summary_all_scored": _summarize(english, exclude_boundary=False),
        "summary_non_boundary": _summarize(english, exclude_boundary=True),
        },
        "professor_de": {
            "rows": professor,
            "summary": _summarize(professor, exclude_boundary=False),
        },
    }

    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    s = out["english_rag_55"]["summary_non_boundary"]
    print(f"Wrote {OUTPUT}")
    print(
        f"English (n={s['n']}, non-boundary): "
        f"P@{DEFAULT_K}={s['precision_at_k']} "
        f"R@{DEFAULT_K}={s['recall_at_k']} "
        f"nDCG@{DEFAULT_K}={s['ndcg_at_k']} "
        f"MRR={s['mrr']} "
        f"overlap={s['source_overlap']}"
    )


if __name__ == "__main__":
    main()
