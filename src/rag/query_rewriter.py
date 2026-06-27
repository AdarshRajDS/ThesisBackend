"""
Produce 2–4 search query variants for hybrid retrieval.
"""

from __future__ import annotations

import re

from src.rag.anatomy_glossary import expand_synonym_query, lookup_canonical
from src.rag.typo_corrector import correct_query


def rewrite_queries(
    question: str,
    *,
    question_type: str = "simple",
    skip_llm: bool = True,
) -> list[str]:
    """
    Return deduplicated query variants (original + corrected + anatomy + corpus-style).
    """
    original = (question or "").strip()
    if not original:
        return []

    corrected, _ = correct_query(original)
    variants: list[str] = [original]

    if corrected.lower() != original.lower():
        variants.append(corrected)

    # Anatomy synonym / corpus-style from detected terms
    lower = corrected.lower()
    for word in re.findall(r"[a-z][a-z\-]+", lower):
        canon = lookup_canonical(word)
        if canon:
            syn_q = f"{canon} anatomy function"
            variants.append(syn_q)
            variants.append(expand_synonym_query(canon))
            break

    # Figure-specific variant
    fig = re.search(r"\bfigure\s+(\d+(?:\.\d+)?)\b", original, re.IGNORECASE)
    if fig:
        fid = fig.group(1)
        variants.append(f"Figure {fid} caption")
        variants.append(f"Figure {fid}")

    # Quote mode: extract key phrases for phrase search
    if question_type == "quote":
        quoted = re.findall(r'"([^"]+)"', original)
        for q in quoted:
            variants.append(q)
        # medical compounds
        for term in (
            "neuromuscular junction",
            "acetylcholine",
            "end plate potential",
            "muscle action potential",
        ):
            if term.replace(" ", "") in lower.replace(" ", ""):
                variants.append(term)

    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        key = v.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(v.strip())

    return out[:4]
