"""Deterministic German → English catalog query translation for Z-Anatomy MCP.

The exportable catalog labels are English (plus Latin). German professor queries
must be rewritten before token/exact matching — not left to the LLM.
"""

from __future__ import annotations

import re
from typing import Iterable

# Longest phrases first (matched against folded lowercase text).
# Values are preferred English / catalog-oriented phrases (not always exact labels).
_GERMAN_PHRASES: list[tuple[str, str]] = [
    ("auge und visuelles system", "accessory visual structures"),
    ("visuelles system", "accessory visual structures"),
    ("musculus quadriceps femoris", "quadriceps femoris muscle"),
    ("m quadriceps femoris", "quadriceps femoris muscle"),
    ("quadriceps femoris", "quadriceps femoris muscle"),
    ("nervus facialis", "facial nerve (vii)"),
    ("n facialis", "facial nerve (vii)"),
    ("gesichtsnerv", "facial nerve (vii)"),
    ("trochanter major", "greater trochanter"),
    ("grosser rollhuegel", "greater trochanter"),
    ("linea aspera", "linea aspera"),
    ("nebenniere", "suprarenal gland"),
    ("nebennieren", "suprarenal gland"),
    ("sprunggelenk", "ankle joint"),
    ("kniegelenk", "knee joint"),
    ("oberschenkelknochen", "femur"),
    ("oberschenkelmuskel", "quadriceps femoris muscle"),
    ("schluesselbein", "clavicle"),
    ("oberschenkel", "femur"),
    ("unterschenkel", "leg"),
    ("handgelenk", "wrist joint"),
    ("schultergelenk", "shoulder joint"),
    ("hueftgelenk", "hip joint"),
    ("rueckenmark", "spinal cord"),
    ("speiche", "radius"),
    ("elle", "ulna"),
    ("pankreas", "pancreas"),
    ("bauchspeicheldruese", "pancreas"),
    ("zwergfell", "diaphragm"),
    ("zwerchfell", "diaphragm"),
    ("milz", "spleen"),
    ("magen", "stomach"),
    ("leber", "liver"),
    ("herz", "heart"),
    ("niere", "kidney"),
    ("nieren", "kidney"),
    ("lunge", "lung"),
    ("lungen", "lung"),
    ("gehirn", "brain"),
    ("hirn", "brain"),
    ("schaedel", "skull"),
    ("auge", "eye"),
    ("augen", "eye"),
    ("ohr", "ear"),
    ("ohren", "ear"),
    ("hand", "hand"),
    ("fuss", "foot"),
    ("knie", "knee"),
    ("huefte", "hip"),
    ("schulter", "shoulder"),
    ("arm", "arm"),
    ("bein", "leg"),
    ("muskel", "muscle"),
    ("muskeln", "muscle"),
    ("knochen", "bone"),
    ("gelenk", "joint"),
    ("incus", "incus"),
    ("amboss", "incus"),
]

# Prefer exact catalog labels when the German term is unambiguous.
GERMAN_TO_CATALOG_LABEL: dict[str, str] = {
    "leber": "Liver",
    "pankreas": "Pancreas",
    "bauchspeicheldruese": "Pancreas",
    "nebenniere": "Suprarenal gland.l",
    "nebennieren": "Suprarenal gland.l",
    "nervus facialis": "Facial nerve (VII)",
    "n facialis": "Facial nerve (VII)",
    "gesichtsnerv": "Facial nerve (VII)",
    "auge und visuelles system": "Accessory visual structures",
    "visuelles system": "Accessory visual structures",
    "incus": "Incus.l",
    "amboss": "Incus.l",
    "linea aspera": "Linea aspera.j",
    "trochanter major": "Greater trochanter.j",
    "grosser rollhuegel": "Greater trochanter.j",
    "musculus quadriceps femoris": "Quadriceps femoris muscle.el",
    "m quadriceps femoris": "Quadriceps femoris muscle.el",
    "quadriceps femoris": "Quadriceps femoris muscle.el",
    "kniegelenk": "Knee joint",
    "sprunggelenk": "Ankle joint",
    "herz": "Heart",
    "magen": "Stomach",
    "milz": "Spleen",
    "zwergfell": "Diaphragm",
    "zwerchfell": "Diaphragm",
    "gehirn": "Brain",
    "niere": "kidney",
    "nieren": "kidney",
}

_SIDE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:linke[rnsm]?|links)\b", re.IGNORECASE), "left"),
    (re.compile(r"\b(?:rechte[rnsm]?|rechts)\b", re.IGNORECASE), "right"),
]

_GERMAN_PREFIX = re.compile(
    r"^(?:bitte\s+)?(?:"
    r"zeig(?:e|t)?(?:\s+mir)?|anzeigen|exportiere|exportieren|"
    r"suche(?:\s+nach)?|finde|oeffne|öffne|lade|gib\s+mir|holen"
    r")\s+(?:mir\s+)?(?:die\s+|den\s+|das\s+|einen?\s+|eine\s+)?",
    re.IGNORECASE,
)
_GERMAN_SUFFIX = re.compile(
    r"\s+(?:bitte|danke|dankeschön|und\s+danke)[.!?\s]*$",
    re.IGNORECASE,
)
_GERMAN_ARTICLES = re.compile(
    r"^(?:die|der|das|den|dem|des|ein|eine|einen|einem|eines)\s+",
    re.IGNORECASE,
)
_GERMAN_TRAILING = re.compile(
    r"\s+(?:organ|struktur|modell|teil|3d|ansicht)$",
    re.IGNORECASE,
)

_UMLAUT_FOLD = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "ae",
        "Ö": "oe",
        "Ü": "ue",
        "ß": "ss",
    }
)


def fold_german(text: str) -> str:
    return (text or "").translate(_UMLAUT_FOLD)


def _sorted_phrases(pairs: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    return sorted(((fold_german(k).lower(), v) for k, v in pairs), key=lambda kv: len(kv[0]), reverse=True)


_PHRASE_MAP = _sorted_phrases(_GERMAN_PHRASES)
_LABEL_MAP = _sorted_phrases(GERMAN_TO_CATALOG_LABEL.items())


def strip_german_command_wrappers(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = _GERMAN_SUFFIX.sub("", cleaned).strip()
    cleaned = _GERMAN_PREFIX.sub("", cleaned).strip()
    cleaned = _GERMAN_ARTICLES.sub("", cleaned).strip()
    cleaned = _GERMAN_TRAILING.sub("", cleaned).strip()
    return cleaned


def translate_side_words(text: str) -> str:
    out = text
    for pattern, replacement in _SIDE_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def lookup_german_catalog_label(text: str) -> str | None:
    """Return an exact preferred catalog label when the whole query is a known German term."""
    folded = fold_german(strip_german_command_wrappers(text)).lower().strip()
    folded = re.sub(r"\s+", " ", folded)
    if not folded:
        return None

    side = None
    body = folded
    for pattern, side_word in _SIDE_PATTERNS:
        if pattern.search(folded):
            side = side_word
            body = pattern.sub(" ", folded)
            body = re.sub(r"\s+", " ", body).strip()
            break

    for phrase, label in _LABEL_MAP:
        if body != phrase and folded != phrase:
            continue
        if side and label.lower() == "kidney":
            return f"Kidney.{'l' if side == 'left' else 'r'}"
        if side and "suprarenal" in label.lower():
            return f"Suprarenal gland.{'l' if side == 'left' else 'r'}"
        if side and label.lower() in {"heart", "liver", "pancreas", "stomach", "spleen", "brain"}:
            return f"{side} {label}"
        if side and not label.endswith((".l", ".r", ".el", ".er", ".j")):
            return f"{side} {label}"
        return label
    return None


def translate_german_anatomy_query(text: str) -> str:
    """
    Rewrite a German (or mixed) anatomy query into an English catalog-oriented phrase.

    Safe to call on English input: unknown tokens are left unchanged.
    """
    exact = lookup_german_catalog_label(text)
    if exact:
        return exact

    cleaned = strip_german_command_wrappers(text)
    cleaned = translate_side_words(cleaned)
    if not cleaned:
        return ""

    # Already looks like an English / catalog label — do not rewrite.
    if re.search(r"\.[a-z]{1,2}$", cleaned, re.IGNORECASE):
        return cleaned
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .()/-]*", cleaned) and any(
        ch.isupper() for ch in cleaned[1:]
    ):
        return cleaned

    working = fold_german(cleaned).lower()
    working = re.sub(r"\s+", " ", working).strip()
    original = working

    for phrase, english in _PHRASE_MAP:
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])")
        working = pattern.sub(f" {english} ", working)

    working = re.sub(r"\s+", " ", working).strip()
    if working == original:
        return cleaned
    return working
