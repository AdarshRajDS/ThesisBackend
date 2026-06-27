from fastapi import APIRouter, Query

from src.config.settings import settings

from app.schemas.anatomy_mcp import (
    AnatomyAskRequest,
    AnatomyAskResult,
    AnatomyExportRequest,
    AnatomyExportResult,
    AnatomySearchResult,
)
from app.services.anatomy_mcp_chat import run_lmstudio_mcp_agent
from app.services.anatomy_mcp_client import (
    call_mcp_tool,
    extract_structured_from_tool_payload,
    get_mcp_bridge,
    structured_to_anatomy_export,
)
from app.services.anatomy_mcp_service import anatomy_mcp_health
from app.services.anatomy_slash import extract_part_query

router = APIRouter(prefix="/anatomy", tags=["Anatomy MCP"])


def _to_export_result(payload: dict, part_query: str | None = None) -> AnatomyExportResult:
    structured = (
        extract_structured_from_tool_payload(payload)
        if isinstance(payload, dict)
        else None
    )
    if isinstance(structured, dict):
        mapped = structured_to_anatomy_export(structured, part_query=part_query)
        if mapped:
            return AnatomyExportResult(**mapped)

    if payload.get("error"):
        return AnatomyExportResult(
            status="error",
            part_query=part_query,
            error=str(payload.get("error")),
            matches=payload.get("matches"),
            instruction=payload.get("instruction"),
        )
    return AnatomyExportResult(
        status="error",
        part_query=part_query,
        error="unexpected_mcp_response",
    )


@router.get("/health")
async def health():
    health_payload = anatomy_mcp_health()
    try:
        bridge = await get_mcp_bridge()
        health_payload["checks"]["mcp_stdio_ok"] = bridge.is_running
        health_payload["checks"]["mcp_stdio_transport"] = "stdio"
    except Exception as exc:
        health_payload["checks"]["mcp_stdio_ok"] = False
        health_payload["checks"]["mcp_stdio_error"] = str(exc)
    return health_payload


@router.get("/search", response_model=AnatomySearchResult)
async def search_catalog(
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(10, ge=1, le=50),
):
    query = extract_part_query(q) or q.strip()
    try:
        result = await run_lmstudio_mcp_agent(
            f"Search the exportable anatomy catalog for '{query}' (limit {limit}). "
            "Use search_anatomy_catalog only; list matches, do not export yet.",
            require_tools=True,
        )
    except Exception as exc:
        return AnatomySearchResult(query=query, error=str(exc))

    answer = result.get("answer", "")
    if result.get("mcp_tools_used"):
        return AnatomySearchResult(
            query=query,
            result_count=0,
            results=[{"summary": answer}],
        )
    return AnatomySearchResult(query=query, error=answer or "search_failed")


@router.post("/ask", response_model=AnatomyAskResult)
async def ask_mcp(req: AnatomyAskRequest):
    """
    LM Studio chooses MCP tools; backend runs call_tool over stdio to anatomy_mcp/server.py.
    """
    try:
        result = await run_lmstudio_mcp_agent(
            req.message.strip(),
            require_tools=True,
            language=req.language,
        )
        return AnatomyAskResult(
            answer=result.get("answer", ""),
            anatomy_export=result.get("anatomy_export"),
            mcp_tools_used=result.get("mcp_tools_used") or [],
            mcp_tool_steps=result.get("mcp_tool_steps") or [],
            mcp_mode=result.get("mcp_mode", "lmstudio_mcp"),
            catalog_info=result.get("catalog_info"),
        )
    except Exception as exc:
        from app.i18n.locale import mcp_ui, normalize_language

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


@router.post("/export", response_model=AnatomyExportResult)
async def export_part(req: AnatomyExportRequest):
    """Export via LM Studio tool-calling (LLM picks search/export tools)."""
    raw_query = (req.part_query or "").strip()
    query = extract_part_query(raw_query) or raw_query
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
        return AnatomyExportResult(**export, part_query=raw_query)

    err = (export or {}).get("error") if export else result.get("answer", "export_failed")
    return AnatomyExportResult(
        status="error",
        part_query=raw_query,
        error=str(err),
        matches=(export or {}).get("matches"),
        instruction=(export or {}).get("instruction"),
    )
