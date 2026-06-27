"""
Build numbered passages for strict RAG prompts (shared with thesis eval).
"""

from __future__ import annotations

import os
from typing import Any


def build_numbered_passages(bundle: dict[str, Any]) -> tuple[str, int]:
    parts: list[str] = []
    n = 1
    for d in bundle.get("text_corpus_docs") or []:
        meta = getattr(d, "metadata", None) or {}
        raw_src = meta.get("source") or meta.get("file_path")
        src = os.path.basename(str(raw_src)) if raw_src else "unknown"
        page = meta.get("page", "?")
        body = (getattr(d, "page_content", None) or "").strip()
        if not body:
            continue
        ctype = meta.get("content_type", "body")
        fig = meta.get("figure_id", "")
        extra = f" | type: {ctype}" + (f" | figure: {fig}" if fig else "")
        parts.append(f"[{n}] Source: {src} | Page: {page}{extra}\n{body}")
        n += 1

    mt = (bundle.get("multimodal_text") or "").strip()
    if mt:
        cap = 3500
        mt_body = mt[:cap] + ("…" if len(mt) > cap else "")
        parts.append(f"[{n}] Source: multimodal_index | Page: n/a\n{mt_body}")
        n += 1

    return "\n\n".join(parts), len(parts)
