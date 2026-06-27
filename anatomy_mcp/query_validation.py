"""Natural-language part queries and vague-input guards for exportable_catalog matching."""

from __future__ import annotations

import re

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9_]+")
SEPARATOR_PATTERN = re.compile(r"_+")

_PART_QUERY_PREFIX = re.compile(
    r"^(?:please\s+)?(?:"
    r"show(?:\s+me)?|display|export|get|give\s+me|open|view|load|find|search(?:\s+for)?"
    r")\s+(?:the\s+)?(?:this\s+)?(?:organ\s+)?",
    re.IGNORECASE,
)
_PART_QUERY_SUFFIX = re.compile(
    r"\s+(?:please|thanks|thank you)[.!?\s]*$",
    re.IGNORECASE,
)

# Normalized tokens that are not usable alone as catalog part_query values.
NON_SPECIFIC_PART_TERMS = frozenset(
    {
        "organ",
        "organs",
        "part",
        "parts",
        "anatomy",
        "body",
        "structure",
        "structures",
        "model",
        "mesh",
        "bone",
        "bones",
        "muscle",
        "muscles",
        "system",
        "human",
        "figure",
        "specimen",
        "thing",
        "area",
        "region",
        "section",
        "export",
        "show",
        "display",
        "view",
        "load",
        "find",
        "search",
        "give",
        "get",
        "me",
        "the",
        "this",
        "that",
        "a",
        "an",
        "please",
        "3d",
    }
)

CLARIFICATION_MESSAGE = (
    "Please name a specific structure from the exportable catalog "
    "(e.g. liver, heart, femur.l, left kidney, Angular gyrus.l)."
)


def normalize_part_query(value: str) -> str:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    normalized = NORMALIZE_PATTERN.sub("_", normalized)
    return SEPARATOR_PATTERN.sub("_", normalized).strip("_")


def extract_part_query(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = _PART_QUERY_SUFFIX.sub("", cleaned).strip()
    cleaned = _PART_QUERY_PREFIX.sub("", cleaned).strip()
    cleaned = re.sub(r"^(?:the|this|organ|a|an)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+(?:organ|structure|model|3d|part|parts)$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def is_vague_part_query(text: str) -> bool:
    """True when no specific exportable label can be inferred (e.g. 'show me the organ')."""
    extracted = extract_part_query(text)
    normalized = normalize_part_query(extracted)
    if not normalized or len(normalized) < 2:
        return True
    if normalized in NON_SPECIFIC_PART_TERMS:
        return True
    tokens = [token for token in normalized.split("_") if token]
    if tokens and all(token in NON_SPECIFIC_PART_TERMS for token in tokens):
        return True
    return False


def looks_like_plain_anatomy_query(text: str) -> bool:
    """Exact catalog labels such as femur.l or Angular gyrus.l."""
    normalized = (text or "").strip()
    if not normalized or len(normalized) > 80:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9 ._-]+", normalized))

def catalog_query_from_user_message(user_message: str) -> str:
    """Prefer extracted structure name; fall back to raw message for exact labels."""
    extracted = extract_part_query(user_message)
    if extracted and not is_vague_part_query(extracted):
        return extracted
    raw = (user_message or "").strip()
    if raw and looks_like_plain_anatomy_query(raw) and not is_vague_part_query(raw):
        return raw
    return extracted or raw
