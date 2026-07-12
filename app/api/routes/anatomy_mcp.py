from fastapi import APIRouter, Query, Request

from src.config.settings import settings

from app.schemas.anatomy_mcp import (
    AnatomyAskRequest,
    AnatomyAskResult,
    AnatomyExportRequest,
    AnatomyExportResult,
    AnatomySearchResult,
    AnatomySuggestRequest,
    AnatomySuggestResult,
    AnatomySuggestionItem,
)
from app.services.anatomy_mcp_chat import (
    build_success_answer,
    run_lmstudio_mcp_agent,
    sanitize_assistant_answer,
)
from app.i18n.locale import normalize_language
from app.services.anatomy_mcp_client import (
    extract_structured_from_tool_payload,
    finalize_anatomy_export,
    rewrite_local_urls,
    structured_to_anatomy_export,
)
from app.services.anatomy_mcp_service import (
    anatomy_mcp_health,
    export_anatomy_part,
    search_anatomy_catalog,
    suggest_exportable_anatomy,
)
from app.services.anatomy_slash import extract_part_query

router = APIRouter(prefix="/anatomy", tags=["Anatomy MCP"])


def _request_origin(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


def _normalize_query(raw: str) -> str:
    return extract_part_query(raw) or raw.strip()


def _suggestion_items(rows: list | None) -> list[AnatomySuggestionItem]:
    if not isinstance(rows, list):
        return []
    out: list[AnatomySuggestionItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        out.append(AnatomySuggestionItem(**{**row, "label": label}))
    return out


def _to_suggest_result(payload: dict, query: str) -> AnatomySuggestResult:
    if payload.get("error"):
        return AnatomySuggestResult(
            status="error",
            query=query,
            error=str(payload.get("error")),
            instruction=payload.get("instruction"),
        )
    suggestions = _suggestion_items(payload.get("suggestions"))
    auto = payload.get("auto_export_candidate")
    auto_item = None
    if isinstance(auto, dict) and auto.get("label"):
        auto_item = AnatomySuggestionItem(**auto)
    return AnatomySuggestResult(
        status=str(payload.get("status") or "suggestions"),
        query=query,
        catalog_query=payload.get("catalog_query"),
        normalized_query=payload.get("normalized_query"),
        catalog_name=payload.get("catalog_name"),
        catalog_path=payload.get("catalog_path"),
        resolver_status=payload.get("resolver_status"),
        suggestions=suggestions,
        suggestion_labels=list(payload.get("suggestion_labels") or []),
        auto_export_candidate=auto_item,
        auto_export_threshold=payload.get("auto_export_threshold"),
    )


def _to_export_result(
    payload: dict,
    part_query: str | None = None,
    *,
    origin: str | None = None,
) -> AnatomyExportResult:
    if origin:
        payload = rewrite_local_urls(payload, origin)
    structured = (
        extract_structured_from_tool_payload(payload)
        if isinstance(payload, dict) and payload.get("structured_content") is not None
        else payload
    )
    if isinstance(structured, dict):
        mapped = structured_to_anatomy_export(structured, part_query=part_query)
        if mapped:
            mapped = finalize_anatomy_export(mapped, origin) if origin else mapped
            suggestions = _suggestion_items(structured.get("suggestions"))
            suggestion_labels = structured.get("suggestion_labels")
            if mapped.get("status") == "error":
                return AnatomyExportResult(
                    **mapped,
                    suggestions=suggestions or None,
                    suggestion_labels=suggestion_labels,
                )
            return AnatomyExportResult(
                **mapped,
                suggestions=suggestions or None,
                suggestion_labels=suggestion_labels,
            )

    if payload.get("error"):
        return AnatomyExportResult(
            status="error",
            part_query=part_query,
            error=str(payload.get("error")),
            matches=payload.get("matches"),
            instruction=payload.get("instruction"),
            suggestions=_suggestion_items(payload.get("suggestions")) or None,
            suggestion_labels=payload.get("suggestion_labels"),
        )
    return AnatomyExportResult(
        status="error",
        part_query=part_query,
        error="unexpected_mcp_response",
    )


@router.get("/health")
async def health(request: Request):
    origin = _request_origin(request)
    health_payload = anatomy_mcp_health(public_api_base=origin)
    try:
        from app.services.anatomy_mcp_client import get_mcp_bridge

        bridge = await get_mcp_bridge()
        health_payload["checks"]["mcp_stdio_ok"] = bridge.is_running
        health_payload["checks"]["mcp_stdio_transport"] = "stdio"
    except Exception as exc:
        health_payload["checks"]["mcp_stdio_ok"] = False
        health_payload["checks"]["mcp_stdio_error"] = str(exc)
    return health_payload


@router.get("/suggest", response_model=AnatomySuggestResult)
async def suggest_catalog_get(
    request: Request,
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(8, ge=1, le=20),
    include_nearby: bool = Query(True),
):
    query = _normalize_query(q)
    origin = _request_origin(request)
    payload = suggest_exportable_anatomy(
        query=query,
        limit=limit,
        include_nearby=include_nearby,
        public_api_base=origin,
    )
    return _to_suggest_result(payload, query)


@router.post("/suggest", response_model=AnatomySuggestResult)
async def suggest_catalog_post(req: AnatomySuggestRequest, request: Request):
    query = _normalize_query(req.query)
    origin = _request_origin(request)
    payload = suggest_exportable_anatomy(
        query=query,
        limit=req.limit,
        include_nearby=req.include_nearby,
        public_api_base=origin,
    )
    return _to_suggest_result(payload, query)


@router.get("/search", response_model=AnatomySearchResult)
async def search_catalog(
    request: Request,
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(10, ge=1, le=50),
):
    """Direct exportable-catalog search (no LLM)."""
    query = _normalize_query(q)
    origin = _request_origin(request)
    try:
        payload = search_anatomy_catalog(query=query, limit=limit, public_api_base=origin)
        if payload.get("error"):
            return AnatomySearchResult(query=query, error=str(payload.get("error")))
        results = payload.get("results") or []
        suggestions = payload.get("suggestions") or []
        return AnatomySearchResult(
            query=query,
            result_count=int(payload.get("result_count") or len(results)),
            results=results,
            suggestions=_suggestion_items(suggestions),
            suggestion_labels=list(payload.get("suggestion_labels") or []),
            resolver_status=payload.get("resolver_status"),
            catalog_name=payload.get("catalog_name"),
        )
    except Exception as exc:
        return AnatomySearchResult(query=query, error=str(exc))


@router.post("/ask", response_model=AnatomyAskResult)
async def ask_mcp(req: AnatomyAskRequest, request: Request):
    """
    LM Studio chooses MCP tools; backend runs call_tool over stdio to anatomy_mcp/server.py.
    """
    try:
        origin = _request_origin(request)
        result = await run_lmstudio_mcp_agent(
            req.message.strip(),
            require_tools=True,
            language=req.language,
        )
        suggestions = result.get("catalog_suggestions") or []
        anatomy_export = result.get("anatomy_export")
        if isinstance(anatomy_export, dict):
            anatomy_export = finalize_anatomy_export(anatomy_export, origin)
        answer = result.get("answer", "")
        if anatomy_export and anatomy_export.get("status") == "ok":
            answer = build_success_answer(
                anatomy_export,
                result.get("mcp_tools_used") or [],
                normalize_language(req.language),
            )
        else:
            answer = sanitize_assistant_answer(
                answer,
                tools_used=result.get("mcp_tools_used") or [],
                language=normalize_language(req.language),
            )
        return AnatomyAskResult(
            answer=answer,
            anatomy_export=anatomy_export,
            mcp_tools_used=result.get("mcp_tools_used") or [],
            mcp_tool_steps=result.get("mcp_tool_steps") or [],
            mcp_mode=result.get("mcp_mode", "lmstudio_mcp"),
            catalog_info=result.get("catalog_info"),
            catalog_suggestions=_suggestion_items(suggestions),
            suggestion_labels=list(result.get("suggestion_labels") or []),
        )
    except Exception as exc:
        from app.i18n.locale import mcp_ui

        lang = normalize_language(req.language)
        return AnatomyAskResult(
            answer=mcp_ui(
                lang,
                "mcp_failed",
                err=str(exc),
                base=settings.llm_api_base,
            ),
            mcp_tools_used=[],
            error=str(exc),
        )


@router.post("/export/direct", response_model=AnatomyExportResult)
async def export_part_direct(req: AnatomyExportRequest, request: Request):
    """Export a catalog label directly via Blender (no LLM)."""
    raw_query = (req.part_query or "").strip()
    query = _normalize_query(raw_query)
    origin = _request_origin(request)
    try:
        payload = export_anatomy_part(
            part_query=query,
            include_preview=req.include_preview,
            region_hint=req.region_hint,
            public_api_base=origin,
        )
        return _to_export_result(payload, part_query=raw_query, origin=origin)
    except ModuleNotFoundError as exc:
        return AnatomyExportResult(
            status="error",
            part_query=raw_query,
            error=f"mcp_not_installed: {exc}. Run: pip install \"mcp[cli]>=1.27.1\"",
        )
    except Exception as exc:
        return AnatomyExportResult(
            status="error",
            part_query=raw_query,
            error=str(exc),
        )


@router.post("/export", response_model=AnatomyExportResult)
async def export_part(req: AnatomyExportRequest, request: Request):
    """Export via LM Studio tool-calling (LLM picks search/export tools)."""
    raw_query = (req.part_query or "").strip()
    query = _normalize_query(raw_query)
    origin = _request_origin(request)
    message = f"Export the 3D anatomy model for: {query}"

    try:
        result = await run_lmstudio_mcp_agent(message, require_tools=True)
    except ModuleNotFoundError as exc:
        return AnatomyExportResult(
            status="error",
            part_query=raw_query,
            error=f"mcp_not_installed: {exc}. Run: pip install \"mcp[cli]>=1.27.1\"",
        )
    except Exception as exc:
        return AnatomyExportResult(
            status="error",
            part_query=raw_query,
            error=str(exc),
        )

    export = result.get("anatomy_export")
    if export and export.get("status") == "ok":
        export = finalize_anatomy_export(export, origin) or export
        return AnatomyExportResult(**export, part_query=raw_query)

    err = (export or {}).get("error") if export else result.get("answer", "export_failed")
    return AnatomyExportResult(
        status="error",
        part_query=raw_query,
        error=str(err),
        matches=(export or {}).get("matches"),
        instruction=(export or {}).get("instruction"),
        suggestions=_suggestion_items(result.get("catalog_suggestions")),
        suggestion_labels=list(result.get("suggestion_labels") or []),
    )
