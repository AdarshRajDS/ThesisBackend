"""Natural-language part queries and vague-input guards for exportable_catalog matching."""

from __future__ import annotations

import re

try:
    from german_anatomy import (
        fold_german,
        lookup_german_catalog_label,
        strip_german_command_wrappers,
        translate_german_anatomy_query,
    )
except ImportError:
    from anatomy_mcp.german_anatomy import (
        fold_german,
        lookup_german_catalog_label,
        strip_german_command_wrappers,
        translate_german_anatomy_query,
    )

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9_]+")
SEPARATOR_PATTERN = re.compile(r"_+")

_PART_QUERY_PREFIX = re.compile(
    r"^(?:please\s+|bitte\s+)?(?:"
    r"show(?:\s+me)?|display|export|get|give\s+me|open|view|load|find|search(?:\s+for)?"
    r"|zeig(?:e|t)?(?:\s+mir)?|anzeigen|exportiere|exportieren|suche(?:\s+nach)?|"
    r"finde|oeffne|öffne|lade|gib\s+mir|holen"
    r")\s+(?:mir\s+)?(?:the\s+|this\s+|die\s+|den\s+|das\s+|einen?\s+|eine\s+)?(?:organ\s+)?",
    re.IGNORECASE,
)
_PART_QUERY_SUFFIX = re.compile(
    r"\s+(?:please|thanks|thank you|bitte|danke|dankeschön)[.!?\s]*$",
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
        # German fillers after command stripping
        "organ",
        "struktur",
        "modell",
        "teil",
        "teile",
        "koerper",
        "korper",
        "bitte",
        "zeig",
        "zeige",
        "mir",
    }
)

CLARIFICATION_MESSAGE = (
    "Please name a specific structure from the exportable catalog "
    "(e.g. liver, heart, femur.l, left kidney, Angular gyrus.l)."
)


def normalize_part_query(value: str) -> str:
    normalized = fold_german(value).lower().replace("-", "_").replace(" ", "_")
    normalized = NORMALIZE_PATTERN.sub("_", normalized)
    return SEPARATOR_PATTERN.sub("_", normalized).strip("_")


def extract_part_query(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = _PART_QUERY_SUFFIX.sub("", cleaned).strip()
    cleaned = _PART_QUERY_PREFIX.sub("", cleaned).strip()
    cleaned = strip_german_command_wrappers(cleaned)
    cleaned = re.sub(
        r"^(?:the|this|organ|a|an|die|der|das|den|dem|ein|eine|einen)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(
        r"\s+(?:organ|structure|model|3d|part|parts|struktur|modell|teil)$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned


def is_vague_part_query(text: str) -> bool:
    """True when no specific exportable label can be inferred (e.g. 'show me the organ')."""
    extracted = extract_part_query(text)
    # Known German anatomy phrases are never vague.
    if lookup_german_catalog_label(extracted or text):
        return False
    translated = translate_german_anatomy_query(extracted or text)
    normalized = normalize_part_query(translated or extracted)
    if not normalized or len(normalized) < 2:
        return True
    if normalized in NON_SPECIFIC_PART_TERMS:
        return True
    tokens = [token for token in normalized.split("_") if token]
    if tokens and all(token in NON_SPECIFIC_PART_TERMS for token in tokens):
        return True
    return False


def looks_like_plain_anatomy_query(text: str) -> bool:
    """Exact catalog labels such as femur.l or Angular gyrus.l (ASCII or German letters)."""
    normalized = (text or "").strip()
    if not normalized or len(normalized) > 80:
        return False
    return bool(re.fullmatch(r"[A-Za-zÀ-ÿ0-9 ._()/-]+", normalized))


def catalog_query_from_user_message(user_message: str) -> str:
    """Prefer extracted structure name; translate German → English catalog phrases."""
    extracted = extract_part_query(user_message)
    candidate = extracted or (user_message or "").strip()

    exact_de = lookup_german_catalog_label(candidate)
    if exact_de:
        return exact_de

    translated = translate_german_anatomy_query(candidate)
    if (
        translated
        and fold_german(translated).lower() != fold_german(candidate).lower()
        and not is_vague_part_query(translated)
    ):
        return translated

    if extracted and not is_vague_part_query(extracted):
        return extracted

    raw = (user_message or "").strip()
    if raw and looks_like_plain_anatomy_query(raw) and not is_vague_part_query(raw):
        raw_translated = translate_german_anatomy_query(raw)
        if (
            raw_translated
            and fold_german(raw_translated).lower() != fold_german(raw).lower()
        ):
            return raw_translated
        return raw
    return translated or extracted or raw
