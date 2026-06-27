"""Parse slash commands and natural-language anatomy part queries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from anatomy_mcp.query_validation import (
    CLARIFICATION_MESSAGE,
    catalog_query_from_user_message,
    extract_part_query,
    is_vague_part_query,
    looks_like_plain_anatomy_query,
)

SlashMode = Literal["export", "search", "help", "none"]

EXPORT_ALIASES = frozenset({"export", "anatomy", "organ", "3d", "mcp", "tool"})
SEARCH_ALIASES = frozenset({"search", "find"})

__all__ = [
    "CLARIFICATION_MESSAGE",
    "SlashIntent",
    "catalog_query_from_user_message",
    "extract_part_query",
    "is_vague_part_query",
    "looks_like_plain_anatomy_query",
    "parse_slash_intent",
]


@dataclass(frozen=True)
class SlashIntent:
    mode: SlashMode
    query: str = ""
    raw: str = ""


def parse_slash_intent(question: str) -> SlashIntent:
    trimmed = (question or "").strip()
    if not trimmed.startswith("/"):
        return SlashIntent(mode="none", query=trimmed, raw=trimmed)

    body = trimmed[1:].strip()
    if not body:
        return SlashIntent(mode="help", raw=trimmed)

    space_idx = body.find(" ")
    cmd = (body if space_idx == -1 else body[:space_idx]).lower()
    args = "" if space_idx == -1 else body[space_idx + 1 :].strip()

    if cmd in EXPORT_ALIASES:
        return SlashIntent(mode="export", query=extract_part_query(args), raw=trimmed)
    if cmd in SEARCH_ALIASES:
        return SlashIntent(mode="search", query=extract_part_query(args), raw=trimmed)
    if cmd in {"help", "commands"}:
        return SlashIntent(mode="help", raw=trimmed)

    if cmd and not args:
        return SlashIntent(mode="export", query=extract_part_query(cmd.replace("_", " ")), raw=trimmed)

    return SlashIntent(mode="none", query=trimmed, raw=trimmed)
