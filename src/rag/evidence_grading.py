"""Heuristic + LLM evidence grading for grounded RAG."""

from __future__ import annotations

import json
import re
from typing import Any

from src.rag.citation_filter import _answer_tokens


def parse_classifier_json(raw: str) -> dict[str, list[int]] | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None
    return None


def _overlap_score(question: str, passage: str) -> float:
    q = _answer_tokens(question)
    p = _answer_tokens(passage)
    if not q or not p:
        return 0.0
    return len(q & p) / max(len(q), 1)


def heuristic_grade_passages(
    question: str,
    indexed_passages: list[tuple[int, str]],
) -> dict[str, list[int]]:
    if not indexed_passages:
        return {"A": [], "B": [], "C": []}

    scored = [
        (idx, _overlap_score(question, body))
        for idx, body in indexed_passages
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    a: list[int] = []
    b: list[int] = []
    c: list[int] = []

    for idx, score in scored:
        if score >= 0.20 and len(a) < 4:
            a.append(idx)
        elif score >= 0.08 and len(b) < 4:
            b.append(idx)
        else:
            c.append(idx)

    if not a and scored:
        a = [scored[0][0]]
        if len(scored) > 1:
            b.append(scored[1][0])

    return {"A": a, "B": b, "C": c}


def merge_grades(
    llm_grades: dict[str, list[int]] | None,
    heuristic: dict[str, list[int]],
    indexed_passages: list[tuple[int, str]],
) -> dict[str, list[int]]:
    valid = {idx for idx, _ in indexed_passages}
    llm = llm_grades or {"A": [], "B": [], "C": []}

    def _clean(raw: Any) -> list[int]:
        out: list[int] = []
        for item in raw or []:
            try:
                idx = int(item)
            except Exception:
                continue
            if idx in valid and idx not in out:
                out.append(idx)
        return out

    a = _clean(llm.get("A")) or list(heuristic.get("A", []))
    b = _clean(llm.get("B")) or list(heuristic.get("B", []))
    used = set(a) | set(b)
    c = [idx for idx in valid if idx not in used]

    if not a and not b:
        a = list(heuristic.get("A", []))
        b = list(heuristic.get("B", []))
        used = set(a) | set(b)
        c = [idx for idx in valid if idx not in used]

    return {"A": a, "B": b, "C": c}


def choose_allowed_passage_ids(
    grades: dict[str, list[int]],
    *,
    question_type: str,
) -> tuple[list[int], str]:
    a_ids = grades.get("A", [])
    b_ids = grades.get("B", [])

    if question_type in ("complex", "thinking", "synthesis", "broad"):
        min_allowed = 2
        max_allowed = 6
    else:
        min_allowed = 1
        max_allowed = 4

    if a_ids:
        allowed = list(dict.fromkeys(a_ids + b_ids[:3]))
        mode = "direct_or_partial"
    elif b_ids:
        allowed = list(dict.fromkeys(b_ids[:max_allowed]))
        mode = "partial_only"
    else:
        return [], "not_found"

    if len(allowed) < min_allowed:
        for idx in b_ids + a_ids:
            if idx not in allowed:
                allowed.append(idx)
            if len(allowed) >= min_allowed:
                break

    return allowed[:max_allowed], mode


def is_abstain_only_answer(answer: str, abstain_phrase: str) -> bool:
    text = (answer or "").strip().lower()
    abstain = (abstain_phrase or "").strip().lower()
    if not text:
        return True
    return text == abstain or text.startswith(abstain)
