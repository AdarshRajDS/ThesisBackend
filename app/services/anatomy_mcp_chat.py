"""
LM Studio (OpenAI-compatible) as MCP host: the LLM chooses tools;
the backend executes them via true MCP stdio (ClientSession.call_tool).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import AsyncOpenAI

from app.i18n.locale import (
    SupportedLanguage,
    build_mcp_system_prompt,
    clarification_message,
    mcp_ui,
    normalize_language,
    resolve_clarification,
)
from anatomy_mcp.query_validation import (
    catalog_query_from_user_message,
    is_vague_part_query,
    looks_like_plain_anatomy_query,
)

from app.services.anatomy_mcp_client import (
    MCPBridge,
    best_catalog_export_match,
    extract_resource_links,
    extract_structured_from_tool_payload,
    extract_timeout_query,
    get_mcp_bridge,
    is_blender_timeout_payload,
    is_mcp_tool_error_payload,
    payload_structured,
    preferred_catalog_options,
    structured_error,
    structured_to_anatomy_export,
)
from src.config.settings import settings

MAX_TOOL_ROUNDS = 6
_ANATOMY_EXPORT_URL_RE = re.compile(
    r"https?://[^\s\)]*/anatomy-(?:exports|viewer)[^\s\)]*",
    re.IGNORECASE,
)


def result_to_text(payload: dict[str, Any]) -> str:
    structured_content = payload.get("structured_content")
    if structured_content:
        return json.dumps(structured_content, ensure_ascii=False)

    text_chunks: list[str] = []
    for item in payload.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            text_chunks.append(item.get("text", ""))

    if text_chunks:
        return "\n".join(chunk for chunk in text_chunks if chunk)

    return json.dumps(payload, ensure_ascii=False)


def _export_structured_from_tool(tool_payload: dict[str, Any]) -> dict[str, Any] | None:
    from app.services.anatomy_mcp_client import normalize_export_structured

    structured = extract_structured_from_tool_payload(tool_payload)
    if not isinstance(structured, dict):
        return None
    normalized = normalize_export_structured(structured)
    if normalized.get("model_url") or normalized.get("viewer_url"):
        return normalized
    return None


def compact_tool_result_for_llm(payload: dict[str, Any]) -> str:
    """Strip package metadata from tool messages so the LLM does not echo every JSON file."""
    structured = extract_structured_from_tool_payload(payload)
    if not isinstance(structured, dict):
        return result_to_text(payload)

    if structured.get("error"):
        compact = {
            key: structured[key]
            for key in ("error", "part_query", "matches", "instruction", "timeout_seconds")
            if structured.get(key) is not None
        }
        return json.dumps(compact, ensure_ascii=False)

    compact: dict[str, Any] = {}
    for key in (
        "part_label",
        "part_query",
        "normalized_query",
        "model_url",
        "annotations_url",
        "viewer_url",
        "annotation_count",
        "result_count",
        "cache_hit",
    ):
        if structured.get(key) is not None:
            compact[key] = structured[key]

    if "results" in structured:
        compact["results"] = structured["results"][:12]

    if compact:
        return json.dumps(compact, ensure_ascii=False)

    return result_to_text(payload)


def build_success_answer(
    export: dict[str, Any],
    tools: list[str],
    language: SupportedLanguage,
) -> str:
    label = export.get("part_label") or export.get("part_query") or "anatomy model"
    if tools:
        return mcp_ui(
            language,
            "exported_via",
            label=label,
            tools=" → ".join(tools),
        )
    return mcp_ui(language, "exported", label=label)


def sanitize_assistant_answer(
    text: str,
    *,
    tools_used: list[str],
    language: SupportedLanguage,
) -> str:
    cleaned = (text or "").strip()

    if _ANATOMY_EXPORT_URL_RE.search(cleaned) and not tools_used:
        return mcp_ui(language, "no_tools")

    if _ANATOMY_EXPORT_URL_RE.search(cleaned):
        cleaned = _ANATOMY_EXPORT_URL_RE.sub("", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        if not cleaned:
            return mcp_ui(language, "export_finished")

    return cleaned or mcp_ui(language, "done")


def _agent_result(
    *,
    answer: str,
    anatomy_export: dict[str, Any] | None = None,
    used_tools: list[str] | None = None,
    tool_steps: list[dict[str, Any]] | None = None,
    resource_links: list[dict[str, str]] | None = None,
    catalog_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "answer": answer,
        "anatomy_export": anatomy_export,
        "mcp_tools_used": used_tools or [],
        "mcp_tool_steps": tool_steps or [],
        "mcp_resources": resource_links or [],
        "mcp_mode": "lmstudio_mcp",
        "catalog_info": catalog_info,
    }


def _catalog_info_from_search(structured: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(structured, dict):
        return {
            "catalog_name": "exportable_catalog.json",
            "resolver_source": "exportable_catalog",
        }
    return {
        "catalog_name": structured.get("catalog_name") or "exportable_catalog.json",
        "catalog_path": structured.get("catalog_path"),
        "catalog_description": structured.get("catalog_description"),
        "source_blend": structured.get("source_blend") or "Startup.blend",
        "resolver_source": structured.get("resolver_source") or "exportable_catalog",
    }


def _suggestion_labels_from_search(
    structured: dict[str, Any] | None,
    *,
    limit: int = 6,
) -> list[str]:
    if not isinstance(structured, dict):
        return []
    explicit = structured.get("suggestions")
    if isinstance(explicit, list) and explicit:
        return [str(label) for label in explicit[:limit]]
    results = structured.get("results")
    if isinstance(results, list) and results:
        return preferred_catalog_options(results, limit=limit)
    return []


def _format_no_exact_match_answer(
    language: SupportedLanguage,
    query: str,
    structured: dict[str, Any] | None,
) -> str:
    info = _catalog_info_from_search(structured)
    catalog = info.get("catalog_name") or "exportable_catalog.json"
    labels = _suggestion_labels_from_search(structured)
    if labels:
        return mcp_ui(
            language,
            "no_exact_with_suggestions",
            query=query,
            catalog=catalog,
            labels=", ".join(labels),
        )
    return mcp_ui(
        language,
        "no_exact_no_suggestions",
        query=query,
        catalog=catalog,
    )


async def _try_catalog_fast_path(
    bridge: MCPBridge,
    user_message: str,
    catalog_query: str,
    language: SupportedLanguage,
) -> dict[str, Any] | None:
    """
    blendermcp-style path: exportable_catalog.json search then direct export for exact labels.
    """
    if not looks_like_plain_anatomy_query(catalog_query):
        return None

    used_tools: list[str] = []
    tool_steps: list[dict[str, Any]] = []

    search_payload = await bridge.call_tool(
        "search_anatomy_catalog",
        {"query": catalog_query, "limit": 12},
    )
    used_tools.append("search_anatomy_catalog")
    tool_steps.append({"name": "search_anatomy_catalog", "arguments": {"query": catalog_query, "limit": 12}})

    if is_mcp_tool_error_payload(search_payload):
        structured = payload_structured(search_payload) or {}
        if structured.get("error") == "query_too_vague":
            return _agent_result(
                answer=resolve_clarification(language, structured.get("instruction")),
            )
        return None

    match = best_catalog_export_match(search_payload, catalog_query)
    if match is not None:
        export_payload = await bridge.call_tool(
            "export_anatomy_part",
            {"part_query": match["label"], "include_preview": False},
        )
        used_tools.append("export_anatomy_part")
        tool_steps.append(
            {
                "name": "export_anatomy_part",
                "arguments": {"part_query": match["label"], "include_preview": False},
            }
        )
        export_structured = _export_structured_from_tool(export_payload)
        export_attachment = structured_to_anatomy_export(export_structured, catalog_query)
        if export_attachment and export_attachment.get("status") == "ok" and export_structured:
            return _agent_result(
                answer=build_success_answer(export_attachment, used_tools, language),
                anatomy_export=export_attachment,
                used_tools=used_tools,
                tool_steps=tool_steps,
                resource_links=extract_resource_links(export_payload),
                catalog_info=_catalog_info_from_search(payload_structured(search_payload)),
            )
        err = structured_error(export_payload) or "export_failed"
        return _agent_result(
            answer=mcp_ui(
                language,
                "export_failed",
                label=match["label"],
                err=err,
            ),
            anatomy_export=export_attachment,
            used_tools=used_tools,
            tool_steps=tool_steps,
        )

    structured = payload_structured(search_payload)
    catalog_info = _catalog_info_from_search(
        structured if isinstance(structured, dict) else None
    )
    labels = _suggestion_labels_from_search(
        structured if isinstance(structured, dict) else None
    )
    if labels:
        return _agent_result(
            answer=_format_no_exact_match_answer(language, catalog_query, structured),
            used_tools=used_tools,
            tool_steps=tool_steps,
            catalog_info=catalog_info,
        )

    if isinstance(structured, dict):
        return _agent_result(
            answer=_format_no_exact_match_answer(language, catalog_query, structured),
            used_tools=used_tools,
            tool_steps=tool_steps,
            catalog_info=catalog_info,
        )

    return None


async def run_lmstudio_mcp_agent(
    user_message: str,
    bridge: MCPBridge | None = None,
    *,
    require_tools: bool = True,
    language: str = "en",
) -> dict[str, Any]:
    """
    Real MCP pattern: LM Studio receives MCP tool schemas and decides call_tool invocations.
    """
    if bridge is None:
        bridge = await get_mcp_bridge()

    lang = normalize_language(language)
    latest = (user_message or "").strip()
    if not latest:
        return _agent_result(answer=mcp_ui(lang, "empty_input"))

    catalog_query = catalog_query_from_user_message(latest)
    if is_vague_part_query(latest):
        return _agent_result(answer=clarification_message(lang))

    fast_path = await _try_catalog_fast_path(bridge, latest, catalog_query, lang)
    if fast_path is not None:
        return fast_path

    lm_client = AsyncOpenAI(
        base_url=settings.llm_api_base,
        api_key=os.getenv("LLM_API_KEY", "lm-studio"),
    )

    user_content = latest
    if catalog_query and catalog_query != latest:
        user_content = f"{latest}\n\n(Catalog part_query: {catalog_query})"

    working_messages = [
        {"role": "system", "content": build_mcp_system_prompt(lang)},
        {"role": "user", "content": user_content},
    ]
    used_tools: list[str] = []
    tool_steps: list[dict[str, Any]] = []
    resource_links: list[dict[str, str]] = []
    successful_export: dict[str, Any] | None = None
    last_export_tool_payload: dict[str, Any] | None = None
    timeout_queries: list[str] = []

    for attempt in range(MAX_TOOL_ROUNDS):
        tools = await bridge.get_openai_tools()
        completion = await lm_client.chat.completions.create(
            model=settings.llm_model,
            messages=working_messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )

        message = completion.choices[0].message
        tool_calls = list(message.tool_calls or [])

        if not tool_calls:
            if require_tools and attempt == 0 and successful_export is None:
                working_messages.append(
                    {
                        "role": "system",
                        "content": mcp_ui(lang, "tool_required"),
                    }
                )
                continue

            if successful_export is None and last_export_tool_payload is not None:
                successful_export = _export_structured_from_tool(last_export_tool_payload)

            export_attachment = structured_to_anatomy_export(successful_export, latest)
            if export_attachment is None and last_export_tool_payload is not None:
                failed_structured = extract_structured_from_tool_payload(
                    last_export_tool_payload
                )
                export_attachment = structured_to_anatomy_export(failed_structured, latest)

            has_export = bool(export_attachment and export_attachment.get("status") == "ok")

            if has_export:
                assistant_text = build_success_answer(
                    export_attachment,
                    used_tools,
                    lang,
                )
            elif any(name.startswith("export_") for name in used_tools):
                last_structured = payload_structured(last_export_tool_payload or {}) or {}
                err = last_structured.get("error") or "export_failed"
                label = (
                    last_structured.get("part_label")
                    or catalog_query_from_user_message(latest)
                    or latest
                )
                assistant_text = mcp_ui(lang, "export_failed", label=label, err=err)
            elif require_tools and not used_tools and not has_export:
                assistant_text = (
                    f"{mcp_ui(lang, 'no_mcp_tools_run')} ({settings.llm_api_base})"
                )
            else:
                assistant_text = sanitize_assistant_answer(
                    message.content or "",
                    tools_used=used_tools,
                    language=lang,
                )
                if require_tools and successful_export is None and not assistant_text:
                    assistant_text = mcp_ui(lang, "mcp_incomplete")

            return {
                "answer": assistant_text,
                "anatomy_export": export_attachment,
                "mcp_tools_used": used_tools,
                "mcp_tool_steps": tool_steps,
                "mcp_resources": resource_links,
                "mcp_mode": "lmstudio_mcp",
            }

        working_messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ],
            }
        )

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            used_tools.append(tool_name)
            arguments: dict[str, Any] = {}
            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError as exc:
                tool_payload = {
                    "is_error": True,
                    "content": [{"type": "text", "text": f"Invalid tool arguments: {exc}"}],
                    "structured_content": None,
                }
            else:
                tool_payload = await bridge.call_tool(tool_name, arguments)
                if tool_name in ("export_anatomy_part", "export_anatomy_package"):
                    last_export_tool_payload = tool_payload
                export_structured = _export_structured_from_tool(tool_payload)
                if export_structured and not is_mcp_tool_error_payload(tool_payload):
                    successful_export = export_structured
                    resource_links = extract_resource_links(tool_payload)

            tool_steps.append({"name": tool_name, "arguments": arguments})
            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": compact_tool_result_for_llm(tool_payload),
                }
            )

            if tool_name == "export_anatomy_part" and is_blender_timeout_payload(
                tool_payload
            ):
                retry_query = extract_timeout_query(
                    tool_payload,
                    str(arguments.get("part_query", latest)),
                )
                timeout_queries.append(retry_query)
                working_messages.append(
                    {
                        "role": "system",
                        "content": mcp_ui(lang, "timeout_retry", query=retry_query),
                    }
                )

    export_attachment = structured_to_anatomy_export(successful_export, latest)
    timeout_note = ""
    if timeout_queries:
        timeout_note = f" Last timeout: '{timeout_queries[-1]}'."

    return {
        "answer": (
            "MCP tool loop ended without a final model export."
            + timeout_note
            + " Try a more specific catalog label (e.g. left kidney)."
        ),
        "anatomy_export": export_attachment,
        "mcp_tools_used": used_tools,
        "mcp_tool_steps": tool_steps,
        "mcp_resources": resource_links,
        "mcp_mode": "lmstudio_mcp",
    }


async def run_anatomy_mcp_question_async(
    question: str,
    *,
    language: str = "en",
) -> dict[str, Any]:
    result = await run_lmstudio_mcp_agent(
        question,
        require_tools=True,
        language=language,
    )
    result["question_type"] = "anatomy_mcp"
    return result
