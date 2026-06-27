"""
Exact-quote extraction from retrieved passages (never invent quotes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MIN_QUOTE_CHARS = 40


@dataclass
class QuoteResult:
    found_exact: bool
    quote_text: str | None
    source_label: str | None
    closest_support: str | None
    message: str


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _longest_verbatim_substring(query: str, passage: str, min_len: int = MIN_QUOTE_CHARS) -> str | None:
    """Find longest substring of passage that appears in query context or is a full sentence."""
    passage_norm = " ".join(passage.split())
    sentences = _split_sentences(passage_norm)
    for sent in sorted(sentences, key=len, reverse=True):
        if len(sent) >= min_len and sent in passage_norm:
            return sent
    return None


def extract_best_quote(
    passages: list[tuple[str, str]],
    query: str,
) -> QuoteResult:
    """
    passages: list of (label, body) e.g. ("[1] page 5", text)
    """
    best_quote = None
    best_label = None
    best_support = None
    best_len = 0

    q_terms = set(re.findall(r"[a-z0-9]+", query.lower()))

    for label, body in passages:
        if not body:
            continue
        for sent in _split_sentences(body):
            if len(sent) < MIN_QUOTE_CHARS:
                continue
            if sent not in body:
                continue
            sent_terms = set(re.findall(r"[a-z0-9]+", sent.lower()))
            overlap = len(q_terms & sent_terms) if q_terms else 0
            if len(sent) > best_len and (overlap >= 1 or len(sent) >= 60):
                best_quote = sent
                best_label = label
                best_len = len(sent)
        if not best_support:
            for sent in _split_sentences(body):
                sent_terms = set(re.findall(r"[a-z0-9]+", sent.lower()))
                if len(q_terms & sent_terms) >= 2:
                    best_support = sent
                    break

    if best_quote:
        return QuoteResult(
            found_exact=True,
            quote_text=best_quote,
            source_label=best_label,
            closest_support=best_support,
            message="",
        )

    no_quote_msg = (
        "I found relevant information, but not an exact quote in the retrieved text."
    )
    support_line = ""
    if best_support:
        support_line = (
            f"\n\nThe closest retrieved support (paraphrase, not a direct quote): "
            f"{best_support}"
        )

    return QuoteResult(
        found_exact=False,
        quote_text=None,
        source_label=None,
        closest_support=best_support,
        message=no_quote_msg + support_line,
    )


def format_quote_answer(result: QuoteResult) -> str:
    if result.found_exact and result.quote_text:
        cite = f" ({result.source_label})" if result.source_label else ""
        return f'"{result.quote_text}"{cite}'
    return result.message
