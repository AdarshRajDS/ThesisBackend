"""
Detect low-value chunk types (TOC, footer, index) from text and metadata.
"""

from __future__ import annotations

import re
from typing import Any

TOC_MARKERS = (
    "table of contents",
    "chapter contents",
    "contents at a glance",
)

FOOTER_MARKERS = (
    "creativecommons",
    "openstax",
    "©",
    "all rights reserved",
    "download for free",
)

INDEX_MARKERS = ("index", "glossary")


def infer_content_type(text: str, metadata: dict[str, Any] | None = None) -> str:
    """Infer content_type when not set at ingest."""
    meta = metadata or {}
    if meta.get("content_type"):
        return str(meta["content_type"])

    t = (text or "").strip()
    lower = t[:400].lower()

    if re.search(r"figure\s+\d+(?:\.\d+)?", lower[:120]):
        return "figure_caption"
    if re.search(r"table\s+\d+", lower[:120]):
        return "table"
    if is_toc_chunk(t):
        return "toc"
    if is_footer_chunk(t):
        return "footer"
    if is_index_chunk(t):
        return "index"
    return "body"


def is_toc_chunk(text: str) -> bool:
    t = (text or "").lower()
    if text.count(".....") > 2:
        return True
    if "chapter" in t[:300] and "...." in t:
        return True
    return any(m in t[:300] for m in TOC_MARKERS)


def is_footer_chunk(text: str) -> bool:
    t = (text or "").lower()
    return any(m in t for m in FOOTER_MARKERS)


def is_index_chunk(text: str) -> bool:
    t = (text or "").lower()
    if "index" in t[:200] and len(t) < 800:
        return True
    return any(m in t[:200] for m in INDEX_MARKERS) and t.count(",") > 15


def content_type_penalty(content_type: str) -> float:
    """Penalty subtracted from support_score."""
    penalties = {
        "toc": 0.45,
        "footer": 0.50,
        "index": 0.40,
        "glossary": 0.35,
    }
    return penalties.get(content_type or "body", 0.0)


def content_type_bonus(content_type: str, question_type: str) -> float:
    if question_type == "multimodal_figure" and content_type == "figure_caption":
        return 0.35
    if content_type == "body":
        return 0.05
    return 0.0
