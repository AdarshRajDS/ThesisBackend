"""
Rule-based question type classification for RAG routing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.rag.query_policy import is_clearly_off_topic_question

QuestionType = Literal[
    "simple",
    "complex",
    "thinking",
    "quote",
    "typo_edge",
    "multimodal_figure",
    "synthesis",
    "out_of_context",
    "broad",
]

QUOTE_PATTERNS = (
    r"\bquote\b",
    r"\bverbatim\b",
    r"exact sentence",
    r"as stated in",
    r"word for word",
    r"from the (?:text|chapter|book)",
)

FIGURE_PATTERN = re.compile(r"\bfigure\s+(\d+(?:\.\d+)?)\b", re.IGNORECASE)
BROAD_PATTERNS = (
    r"tell me everything",
    r"overview of",
    r"everything about",
    r"all about the",
)


@dataclass
class QuestionClassification:
    question_type: QuestionType
    figure_id: str | None = None
    assumed_correction: str | None = None


def _looks_like_typo(question: str) -> bool:
    q = question.lower()
    # Missing vowels, repeated consonants, no spaces in compound
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", q):
        return True
    if re.search(r"\bwat\b", q):
        return True
    if re.search(r"broinstem|thalamous|synaps\b|gray mater\b", q):
        return True
    return False


def classify_question(question: str) -> QuestionClassification:
    q = (question or "").strip()
    lower = q.lower()

    if is_clearly_off_topic_question(q):
        return QuestionClassification(question_type="out_of_context")

    for pat in QUOTE_PATTERNS:
        if re.search(pat, lower):
            return QuestionClassification(question_type="quote")

    fig = FIGURE_PATTERN.search(q)
    if fig:
        return QuestionClassification(
            question_type="multimodal_figure",
            figure_id=fig.group(1),
        )

    for pat in BROAD_PATTERNS:
        if re.search(pat, lower):
            return QuestionClassification(question_type="broad")

    if _looks_like_typo(q):
        return QuestionClassification(question_type="typo_edge")

    if any(w in lower for w in ("compare", "difference between", "versus", " vs ")):
        return QuestionClassification(question_type="complex")

    if any(
        w in lower
        for w in ("why ", "how does", "explain", "pathway", "trace", "from receptor")
    ):
        if "step" in lower or "pathway" in lower or "trace" in lower:
            return QuestionClassification(question_type="synthesis")
        return QuestionClassification(question_type="thinking")

    if len(q.split()) > 18 or q.count("?") > 0 and " and " in lower:
        return QuestionClassification(question_type="complex")

    return QuestionClassification(question_type="simple")


def max_passages_for_type(question_type: QuestionType) -> int:
    caps = {
        "simple": 4,
        "complex": 8,
        "thinking": 8,
        "quote": 6,
        "typo_edge": 5,
        "multimodal_figure": 6,
        "synthesis": 8,
        "broad": 6,
        "out_of_context": 0,
    }
    return caps.get(question_type, 4)
