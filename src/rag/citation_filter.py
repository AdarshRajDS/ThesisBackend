"""
Filter citations to those that support the answer and drop TOC/footer noise.
"""

from __future__ import annotations

import re
from typing import Any

from src.rag.content_heuristics import infer_content_type, is_footer_chunk, is_toc_chunk


def _answer_tokens(answer: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (answer or "").lower()) if len(w) > 3}


def passage_supports_answer(
    answer: str,
    chunk_preview: str,
    *,
    min_overlap: int = 2,
) -> bool:
    a_t = _answer_tokens(answer)
    p_t = _answer_tokens(chunk_preview)
    if not a_t or not p_t:
        return False
    return len(a_t & p_t) >= min_overlap


def filter_sources_pre_generation(
    sources: list[dict[str, Any]],
    *,
    min_support_score: float = 0.10,
) -> list[dict[str, Any]]:
    """Drop TOC/footer and low support_score passages before prompting."""
    out = []
    for s in sources:
        preview = s.get("chunk_preview") or ""
        ctype = infer_content_type(preview, s)
        if ctype in ("toc", "footer", "index"):
            continue
        if is_toc_chunk(preview) or is_footer_chunk(preview):
            continue
        sc = s.get("support_score")
        if sc is not None and sc < min_support_score:
            continue
        out.append(s)
    return out


def filter_sources_post_generation(
    answer: str,
    sources: list[dict[str, Any]] | None,
    *,
    min_overlap: int = 2,
    min_sources: int = 1,
    max_sources: int = 3,
    preferred_passage_ids: list[int] | None = None,
) -> list[dict[str, Any]] | None:
    """Prefer evidence passages used for generation; keep at least min_sources."""
    if not sources:
        return sources

    kept: list[dict[str, Any]] = []
    seen: set[int] = set()

    for pid in preferred_passage_ids or []:
        if pid < 1 or pid > len(sources) or pid in seen:
            continue
        item = dict(sources[pid - 1])
        item["passage_id"] = pid
        kept.append(item)
        seen.add(pid)

    for s in sources:
        preview = s.get("chunk_preview") or ""
        if passage_supports_answer(answer, preview, min_overlap=min_overlap):
            pid = sources.index(s) + 1
            if pid in seen:
                continue
            item = dict(s)
            item["passage_id"] = pid
            kept.append(item)
            seen.add(pid)

    if min_sources > 0 and len(kept) < min_sources:
        return None
    if max_sources > 0:
        kept = kept[:max_sources]
    return kept or None
