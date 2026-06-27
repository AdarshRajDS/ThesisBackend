"""
Verify answer sentences are supported by retrieved passages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.rag.citation_filter import _answer_tokens


@dataclass
class VerificationResult:
    support_score: float
    unsupported_sentences: list[str]
    revised_answer: str | None


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 10]


def _passage_blob(passages: list[str]) -> set[str]:
    tokens: set[str] = set()
    for p in passages:
        tokens |= _answer_tokens(p)
    return tokens


def verify_answer(
    answer: str,
    passage_bodies: list[str],
    *,
    min_overlap: int = 3,
    add_caveat: bool = False,
) -> VerificationResult:
    if not answer or not passage_bodies:
        return VerificationResult(
            support_score=0.0,
            unsupported_sentences=[],
            revised_answer=None,
        )

    p_tokens = _passage_blob(passage_bodies)
    sentences = _split_sentences(answer)
    if not sentences:
        return VerificationResult(support_score=1.0, unsupported_sentences=[], revised_answer=None)

    unsupported: list[str] = []
    supported_count = 0

    for sent in sentences:
        s_t = _answer_tokens(sent)
        if not s_t:
            continue
        overlap = len(s_t & p_tokens)
        if overlap >= min_overlap or len(sent) < 30:
            supported_count += 1
        else:
            unsupported.append(sent)

    support_score = supported_count / max(len(sentences), 1)
    revised = None

    if unsupported and add_caveat and support_score < 0.85:
        caveat = (
            "\n\n(Note: Some statements above are inferred from the retrieved passages "
            "rather than quoted directly.)"
        )
        if caveat.strip() not in answer:
            revised = answer.rstrip() + caveat

    return VerificationResult(
        support_score=round(support_score, 3),
        unsupported_sentences=unsupported,
        revised_answer=revised,
    )


def compute_confidence(
    *,
    retrieval_scores: list[float],
    answer_support_score: float,
    had_retrieved: bool,
    question_type: str,
    corpus_fit: bool = True,
) -> dict:
    if not had_retrieved:
        retrieval_conf = 0.0
    elif retrieval_scores:
        retrieval_conf = min(1.0, sum(retrieval_scores) / len(retrieval_scores))
    else:
        retrieval_conf = 0.3

    citation_quality = min(1.0, answer_support_score * 0.9 + (0.1 if retrieval_conf > 0.2 else 0))

    overall = (
        0.30 * retrieval_conf
        + 0.35 * answer_support_score
        + 0.20 * citation_quality
        + (0.15 if corpus_fit else 0.0)
    )

    return {
        "retrieval_confidence": round(retrieval_conf, 3),
        "answer_support": round(answer_support_score, 3),
        "citation_quality": round(citation_quality, 3),
        "corpus_fit": corpus_fit,
        "overall": round(overall, 3),
        "question_type": question_type,
    }
