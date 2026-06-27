"""
Medical/anatomy spelling correction using glossary + fuzzy match.
"""

from __future__ import annotations

import difflib
import re

from src.rag.anatomy_glossary import GLOSSARY, lookup_canonical, variants_for


def _tokens(question: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", question or "")


def correct_query(question: str) -> tuple[str, str | None]:
    """
    Return (corrected_question, assumption_note).
    assumption_note is set when a silent correction was applied.
    """
    q = (question or "").strip()
    if not q:
        return q, None

    lower = q.lower()
    assumption_parts: list[str] = []

    # Whole-phrase glossary hits (longest first)
    for canonical, variants in sorted(GLOSSARY.items(), key=lambda x: -max(len(v) for v in x[1])):
        for v in variants:
            if len(v) < 4:
                continue
            if v.lower() in lower and v.lower() != canonical.lower():
                pattern = re.compile(re.escape(v), re.IGNORECASE)
                q = pattern.sub(canonical, q)
                assumption_parts.append(f"{v} → {canonical}")

    # Token-level fuzzy match against glossary keys
    words = _tokens(q)
    all_terms: list[str] = []
    for canonical, variants in GLOSSARY.items():
        all_terms.append(canonical)
        all_terms.extend(variants)

    for word in words:
        if len(word) < 5:
            continue
        canon = lookup_canonical(word)
        if canon:
            if word.lower() != canon.lower():
                q = re.sub(re.escape(word), canon, q, flags=re.IGNORECASE)
                assumption_parts.append(f"{word} → {canon}")
            continue
        matches = difflib.get_close_matches(word.lower(), [t.lower() for t in all_terms], n=1, cutoff=0.82)
        if matches:
            matched = matches[0]
            canon = lookup_canonical(matched) or matched
            if word.lower() != canon.lower():
                q = re.sub(re.escape(word), canon, q, flags=re.IGNORECASE)
                assumption_parts.append(f"{word} → {canon}")

    # Common typo patterns
    replacements = [
        (r"\bwat\b", "what"),
        (r"\bbroinstem\b", "brain stem"),
        (r"\bthalamous\b", "thalamus"),
        (r"\bsynaps\b", "synapse"),
        (r"\bgray mater\b", "gray matter"),
        (r"\bwhite mater\b", "white matter"),
    ]
    for pat, repl in replacements:
        if re.search(pat, lower):
            q = re.sub(pat, repl, q, flags=re.IGNORECASE)
            assumption_parts.append(f"spelling correction applied")

    note = None
    if assumption_parts:
        unique = list(dict.fromkeys(assumption_parts))
        note = "I assume you mean: " + "; ".join(unique[:3]) + "."
    return q, note
