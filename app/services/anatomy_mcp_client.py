"""True Model Context Protocol client for ``anatomy_mcp/server.py`` (stdio transport)."""

from __future__ import annotations

import asyncio
import functools
import json
import os
import re
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from mcp import ClientSession, StdioServerParameters, types as mcp_types
from mcp.client.stdio import stdio_client

from app.services.anatomy_mcp_service import configure_anatomy_mcp_urls, _ensure_pywin32
from src.config.settings import settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ANATOMY_MCP_ROOT = _REPO_ROOT / "anatomy_mcp"
_MCP_SERVER_PY = _ANATOMY_MCP_ROOT / "server.py"
_EXPORTABLE_CATALOG_PATH = _ANATOMY_MCP_ROOT / "label_index" / "exportable_catalog.json"
MCP_BRIDGE_START_TIMEOUT_SECONDS = 20.0


def _normalize_catalog_label(value: str) -> str:
    """Match ``build_exportable_catalog.normalize_label`` exactly so queries line up with normalized_label."""
    normalized = (value or "").lower().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


@functools.lru_cache(maxsize=1)
def _exportable_catalog_label_maps() -> tuple[dict[str, str], dict[str, frozenset[str]]]:
    """
    Build lookup maps from exportable_catalog.json for exact-label resolution:
      - exact: lower(label) -> canonical label (object entries preferred)
      - normalized: normalized_label -> frozenset of canonical labels
    Only entries that are exportable geometry are indexed, so any hit is renderable.
    """
    exact: dict[str, str] = {}
    normalized_acc: dict[str, set[str]] = {}
    try:
        data = json.loads(_EXPORTABLE_CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}

    for entry in data.get("entries", []):
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        match_type = entry.get("match_type")
        key = label.lower()
        # Prefer object entries when a label collides with a collection.
        if key not in exact or match_type == "object":
            exact[key] = label
        norm = str(entry.get("normalized_label") or "") or _normalize_catalog_label(label)
        if norm:
            normalized_acc.setdefault(norm, set()).add(label)

    normalized = {key: frozenset(values) for key, values in normalized_acc.items()}
    return exact, normalized


def resolve_exact_catalog_label(query: str) -> str | None:
    """
    Return the canonical catalog label when ``query`` is unambiguously an exact
    catalog entry (by literal label or normalized label). Returns None for
    fuzzy/ambiguous input so those keep flowing through the LLM tool-calling loop.
    """
    text = (query or "").strip()
    if not text:
        return None

    exact, normalized = _exportable_catalog_label_maps()
    if not exact:
        return None

    direct = exact.get(text.lower())
    if direct:
        return direct

    labels = normalized.get(_normalize_catalog_label(text))
    if labels and len(labels) == 1:
        return next(iter(labels))
    return None

_bridge: Optional["MCPBridge"] = None
_bridge_lock = asyncio.Lock()


@dataclass
class MCPClientConfig:
    python_executable: str
    mcp_server_py: str
    public_api_base: str
    repo_root: str

    @classmethod
    def from_settings(cls) -> "MCPClientConfig":
        configure_anatomy_mcp_urls(settings.public_api_base)
        return cls(
            python_executable=sys.executable,
            mcp_server_py=str(_MCP_SERVER_PY),
            public_api_base=(settings.public_api_base or "http://127.0.0.1:8000").rstrip("/"),
            repo_root=str(_REPO_ROOT),
        )

    def subprocess_env(self) -> dict[str, str]:
        """
        Environment for the MCP server subprocess.

        The server (``anatomy_mcp/server.py``) and its sibling modules use a mix
        of flat imports (``from config import ...``) and absolute package imports
        (``from anatomy_mcp.catalog_search import ...``). Running the script puts
        only ``anatomy_mcp/`` on ``sys.path``, so the absolute imports fail with
        ``No module named 'anatomy_mcp'`` unless the repo root is on PYTHONPATH.
        """
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        parts = [self.repo_root] + ([existing] if existing else [])
        env["PYTHONPATH"] = os.pathsep.join(parts)
        return env


def build_anatomy_viewer_url(
    app_origin: str,
    model_url: str,
    annotations_url: str,
) -> str:
    """Canonical viewer URL — always derived from the live API origin."""
    base = (app_origin or "http://127.0.0.1:8000").rstrip("/")
    return (
        f"{base}/anatomy-viewer/index.html"
        f"?model={quote(model_url, safe='')}"
        f"&annotations={quote(annotations_url, safe='')}"
    )


def finalize_anatomy_export(
    export: dict[str, Any] | None,
    app_origin: str,
) -> dict[str, Any] | None:
    """
    Normalize every export payload before it reaches the UI:
    rewrite stale localhost ports and rebuild viewer_url from model + annotations.
    """
    if not isinstance(export, dict):
        return None

    origin = (app_origin or "http://127.0.0.1:8000").rstrip("/")
    finalized = rewrite_local_urls(dict(export), origin)
    if finalized.get("status") != "ok":
        return finalized

    model_url = finalized.get("model_url")
    annotations_url = finalized.get("annotations_url")
    if model_url and annotations_url:
        finalized["viewer_url"] = build_anatomy_viewer_url(
            origin,
            str(model_url),
            str(annotations_url),
        )
    elif model_url or annotations_url or finalized.get("preview_url"):
        for key in ("model_url", "annotations_url", "viewer_url", "preview_url"):
            if finalized.get(key):
                finalized[key] = rewrite_local_urls(finalized[key], origin)

    return finalized


def rewrite_mcp_payload(payload: dict[str, Any], app_origin: str) -> dict[str, Any]:
    """Rewrite URLs inside an MCP tool payload (structured + text content)."""
    if not isinstance(payload, dict):
        return payload
    return rewrite_local_urls(payload, app_origin)


def make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump(exclude_none=True))
    if hasattr(value, "dict"):
        return make_json_safe(value.dict(exclude_none=True))
    return str(value)


def rewrite_local_urls(value: Any, app_origin: str) -> Any:
    if isinstance(value, dict):
        return {key: rewrite_local_urls(item, app_origin) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_local_urls(item, app_origin) for item in value]
    if isinstance(value, str):
        origin = (app_origin or "").rstrip("/")
        if not origin:
            return value
        rewritten = value
        stale_origins = (
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8123",
            "http://127.0.0.1:8123",
            "http://localhost:8001",
            "http://127.0.0.1:8001",
        )
        for stale in stale_origins:
            if stale in rewritten and origin not in rewritten:
                rewritten = rewritten.replace(stale, origin)
        if "/anatomy-exports/" in rewritten or "/anatomy-viewer/" in rewritten:
            try:
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(rewritten)
                if parsed.path.startswith("/anatomy-"):
                    parsed = parsed._replace(scheme=urlparse(origin).scheme, netloc=urlparse(origin).netloc)
                    rewritten = urlunparse(parsed)
            except Exception:
                pass
        return rewritten
    return value


def requires_mcp_tool(user_message: str) -> bool:
    normalized = user_message.lower()
    keywords = (
        "anatomy",
        "organ",
        "liver",
        "heart",
        "kidney",
        "thalamus",
        "brain",
        "viewer",
        "annotation",
        "annotations",
        "package",
        "export",
        "glb",
        "blend",
        "study",
        "femur",
        "stomach",
        "pancreas",
        "skull",
        "cor",
        "hepar",
    )
    return any(keyword in normalized for keyword in keywords)


def looks_like_plain_anatomy_query(user_message: str) -> bool:
    normalized = user_message.strip()
    if not normalized or len(normalized) > 80:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9 ._-]+", normalized))


def structured_error(payload: dict[str, Any]) -> str | None:
    structured = payload.get("structured_content")
    if isinstance(structured, dict):
        error = structured.get("error")
        return str(error) if error else None
    return None


def payload_structured(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Read tool JSON from structuredContent or FastMCP text content."""
    if not isinstance(payload, dict):
        return None
    if payload.get("results") is not None or payload.get("normalized_query") is not None:
        return payload
    return extract_structured_from_tool_payload(payload)


def exact_catalog_match(payload: dict[str, Any], query: str = "") -> dict[str, Any] | None:
    structured = payload_structured(payload)
    if not isinstance(structured, dict):
        return None

    normalized_query = str(structured.get("normalized_query") or "").lower()
    if not normalized_query and query:
        from anatomy_mcp.query_validation import normalize_part_query

        normalized_query = normalize_part_query(query)
    candidates = [
        result
        for result in structured.get("results", [])
        if isinstance(result, dict) and result.get("match_reason") in {"exact_label", "resolved_query"}
    ]
    candidates = [
        result
        for result in candidates
        if result.get("match_reason") == "resolved_query"
        or str(result.get("label", "")).lower().replace("-", "_").replace(" ", "_") == normalized_query
    ]
    unique_candidates = {}
    for candidate in candidates:
        key = candidate.get("id") or candidate.get("label")
        unique_candidates[str(key)] = candidate

    if len(unique_candidates) == 1:
        return next(iter(unique_candidates.values()))
    return None


def best_catalog_export_match(payload: dict[str, Any], query: str) -> dict[str, Any] | None:
    """Pick a single export target for plain-language queries (e.g. left femur → Femur.l)."""
    structured = payload_structured(payload)
    if not isinstance(structured, dict):
        return None

    resolved = exact_catalog_match(structured, query)
    if resolved is not None:
        return resolved

    from anatomy_mcp.catalog_search import desired_side_from_tokens, extract_query_tokens
    from anatomy_mcp.query_validation import catalog_query_from_user_message, normalize_part_query

    catalog_query = catalog_query_from_user_message(query)
    query_tokens = extract_query_tokens(normalize_part_query(catalog_query))
    want_side = desired_side_from_tokens(query_tokens)
    content_tokens = [t for t in query_tokens if t not in {"left", "right", "l", "r"}]

    results = structured.get("results") or []
    objects = [r for r in results if isinstance(r, dict) and r.get("match_type") == "object"]
    if not objects:
        return None

    def side_ok(item: dict[str, Any]) -> bool:
        if not want_side:
            return True
        label_lower = str(item.get("label") or "").lower()
        if want_side == "left":
            return item.get("side") == "left" or label_lower.endswith(".l")
        return item.get("side") == "right" or label_lower.endswith(".r")

    pool = [r for r in objects if side_ok(r)]
    if not pool:
        pool = list(objects)

    if content_tokens:
        narrowed = []
        for item in pool:
            label_norm = str(item.get("label") or "").lower().replace(".", "_").replace(" ", "_")
            if all(token in label_norm for token in content_tokens):
                narrowed.append(item)
        if narrowed:
            pool = narrowed

    pool.sort(key=lambda item: (len(str(item.get("label") or "")), str(item.get("label") or "").lower()))
    if len(pool) == 1:
        return pool[0]
    return None


def preferred_catalog_options(results: list[dict[str, Any]], limit: int = 6) -> list[str]:
    object_results = [result for result in results if result.get("match_type") == "object"]
    lateral_results = [result for result in object_results if result.get("side") in {"left", "right"}]
    source = lateral_results or object_results or results
    labels = []
    seen = set()
    for result in source:
        label = str(result.get("label") or "")
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def structured_suggestion_labels(structured: dict[str, Any] | None, *, limit: int = 6) -> list[str]:
    if not isinstance(structured, dict):
        return []
    explicit = structured.get("suggestion_labels")
    if isinstance(explicit, list) and explicit:
        return [str(label) for label in explicit[:limit]]

    suggestions = structured.get("suggestions")
    if isinstance(suggestions, list) and suggestions:
        if suggestions and isinstance(suggestions[0], dict):
            return preferred_catalog_options(suggestions, limit=limit)
        return [str(label) for label in suggestions[:limit]]

    results = structured.get("results")
    if isinstance(results, list) and results:
        return preferred_catalog_options(results, limit=limit)
    return []


def format_structured_suggestions_for_user(
    structured: dict[str, Any] | None,
    *,
    limit: int = 6,
) -> str:
    if not isinstance(structured, dict):
        return ""
    suggestions = structured.get("suggestions")
    if not isinstance(suggestions, list):
        return ""

    lines: list[str] = []
    for row in suggestions[:limit]:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        reason = str(row.get("match_reason") or "suggested")
        confidence = row.get("confidence")
        if confidence is not None:
            lines.append(f"- {label} ({reason}, confidence={confidence})")
        else:
            lines.append(f"- {label} ({reason})")
    return "\n".join(lines)


def auto_export_candidate_from_structured(structured: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(structured, dict):
        return None
    candidate = structured.get("auto_export_candidate")
    if isinstance(candidate, dict) and candidate.get("label"):
        return candidate
    suggestions = structured.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        return None
    top = suggestions[0]
    if not isinstance(top, dict):
        return None
    threshold = float(structured.get("auto_export_threshold") or 0.95)
    if float(top.get("confidence") or 0) >= threshold and top.get("can_export"):
        return top
    return None


def is_blender_timeout_payload(payload: dict[str, Any]) -> bool:
    structured = payload.get("structured_content")
    if isinstance(structured, dict) and structured.get("error") == "blender_timeout":
        return True

    for item in payload.get("content", []):
        text = item.get("text", "") if isinstance(item, dict) else ""
        if "blender_timeout" in text:
            return True

    return False


def is_mcp_tool_error_payload(payload: dict[str, Any]) -> bool:
    if bool(payload.get("is_error")):
        return True

    structured = payload.get("structured_content")
    if isinstance(structured, dict) and structured.get("error"):
        return True

    for item in payload.get("content", []):
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("error"):
            return True

    return False


def extract_timeout_query(payload: dict[str, Any], fallback_query: str) -> str:
    structured = payload.get("structured_content")
    if isinstance(structured, dict):
        return str(structured.get("part_query") or fallback_query)
    return fallback_query


def prettify_resource_key(key: str) -> str:
    cleaned = key.removesuffix("_url").replace("_", " ").strip()
    return cleaned.title() if cleaned else "Resource"


def extract_resource_links(payload: dict[str, Any]) -> list[dict[str, str]]:
    discovered: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def visit(value: Any, parent_key: str | None = None) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, key)
            return
        if isinstance(value, list):
            for item in value:
                visit(item, parent_key)
            return
        if not isinstance(value, str):
            return
        if not value.startswith(("http://", "https://")):
            return

        label = prettify_resource_key(parent_key or "resource")
        if value in seen_urls:
            return
        seen_urls.add(value)
        discovered.append({"label": label, "url": value})

    structured = payload.get("structured_content")
    if structured:
        visit(structured)

    for item in payload.get("content", []):
        if isinstance(item, dict):
            uri = item.get("uri")
            if isinstance(uri, str):
                visit(uri, item.get("type") or "resource")

    return discovered


def extract_structured_from_tool_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """FastMCP often returns tool JSON in text content, not structuredContent."""
    structured = payload.get("structured_content")
    if isinstance(structured, dict) and structured:
        return structured

    for item in payload.get("content", []):
        if not isinstance(item, dict) or item.get("type") != "text":
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_export_structured(structured: dict[str, Any]) -> dict[str, Any]:
    """Ensure package exports expose the same three URLs as single-part exports."""
    normalized = dict(structured)
    files = normalized.get("files")
    if isinstance(files, dict):
        if not normalized.get("model_url"):
            glb_url = files.get("anatomy_glb") or files.get("anatomy")
            if glb_url:
                normalized["model_url"] = glb_url
        if not normalized.get("annotations_url"):
            ann_url = files.get("annotations_json") or files.get("annotations")
            if ann_url:
                normalized["annotations_url"] = ann_url
    return normalized


def structured_to_anatomy_export(
    structured: dict[str, Any] | None,
    part_query: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(structured, dict):
        return None

    structured = normalize_export_structured(structured)

    if structured.get("error"):
        error_code = str(structured.get("error"))
        message = structured.get("instruction") or error_code
        if error_code == "query_too_vague":
            message = structured.get("instruction") or message
        return {
            "status": "error",
            "part_query": part_query or structured.get("part_query"),
            "error": message if error_code == "query_too_vague" else error_code,
            "matches": structured.get("matches") or structured.get("suggestion_labels"),
            "instruction": structured.get("instruction"),
            "suggestions": structured.get("suggestions"),
            "suggestion_labels": structured.get("suggestion_labels"),
        }

    if not structured.get("model_url"):
        return None

    export = {
        "status": "ok",
        "part_query": part_query or structured.get("part_label"),
        "part_label": structured.get("part_label"),
        "model_url": structured.get("model_url"),
        "annotations_url": structured.get("annotations_url"),
        "viewer_url": structured.get("viewer_url"),
        "preview_url": structured.get("preview_url"),
        "source_blend": structured.get("source_blend"),
        "selected_objects": structured.get("selected_objects"),
        "annotation_labels": structured.get("annotation_labels"),
        "annotation_count": structured.get("annotation_count"),
        "cache_hit": structured.get("cache_hit"),
    }
    return export


class MCPBridge:
    def __init__(self, config: MCPClientConfig) -> None:
        self.config = config
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._session is not None

    async def start(self) -> None:
        if self._session is not None:
            return

        _ensure_pywin32()
        configure_anatomy_mcp_urls(self.config.public_api_base)

        if not Path(self.config.mcp_server_py).exists():
            raise FileNotFoundError(f"MCP server not found: {self.config.mcp_server_py}")

        stack = AsyncExitStack()
        server_params = StdioServerParameters(
            command=self.config.python_executable,
            args=[self.config.mcp_server_py],
            env=self.config.subprocess_env(),
            cwd=self.config.repo_root,
        )

        read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        self._stack = stack
        self._session = session

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    async def list_tools(self) -> list[Any]:
        if self._session is None:
            raise RuntimeError("MCP session is not initialized")

        async with self._lock:
            result = await self._session.list_tools()
        return list(result.tools)

    async def get_openai_tools(self) -> list[dict[str, Any]]:
        tools = await self.list_tools()
        openai_tools: list[dict[str, Any]] = []

        for tool in tools:
            schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
            schema = make_json_safe(schema)
            if not isinstance(schema, dict):
                schema = {"type": "object", "properties": {}}
            if "type" not in schema:
                schema["type"] = "object"
            if "properties" not in schema:
                schema["properties"] = {}

            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": schema,
                    },
                }
            )

        return openai_tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("MCP session is not initialized")

        async with self._lock:
            result = await self._session.call_tool(name, arguments)

        payload = self._serialize_call_tool_result(result)
        return rewrite_local_urls(payload, self.config.public_api_base)

    def _serialize_call_tool_result(self, result: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "is_error": bool(getattr(result, "isError", False)),
            "structured_content": make_json_safe(getattr(result, "structuredContent", None)),
            "content": [],
        }

        for item in getattr(result, "content", []):
            if isinstance(item, mcp_types.TextContent):
                payload["content"].append({"type": "text", "text": item.text})
            elif isinstance(item, mcp_types.ImageContent):
                payload["content"].append(
                    {
                        "type": "image",
                        "mime_type": item.mimeType,
                        "data": item.data,
                    }
                )
            elif isinstance(item, mcp_types.EmbeddedResource):
                resource = item.resource
                entry: dict[str, Any] = {
                    "type": "resource",
                    "uri": getattr(resource, "uri", None),
                    "mime_type": getattr(resource, "mimeType", None),
                }
                if isinstance(resource, mcp_types.TextResourceContents):
                    entry["text"] = resource.text
                elif isinstance(resource, getattr(mcp_types, "BlobResourceContents", ())):
                    entry["blob"] = resource.blob
                payload["content"].append(entry)
            else:
                payload["content"].append({"type": "unknown", "value": make_json_safe(item)})

        return payload


async def get_mcp_bridge() -> MCPBridge:
    global _bridge
    async with _bridge_lock:
        if _bridge is None:
            _bridge = MCPBridge(MCPClientConfig.from_settings())
        if not _bridge.is_running:
            try:
                await asyncio.wait_for(
                    _bridge.start(),
                    timeout=MCP_BRIDGE_START_TIMEOUT_SECONDS,
                )
            except Exception:
                _bridge = None
                raise
        return _bridge


async def start_mcp_bridge() -> None:
    if not settings.anatomy_mcp_enabled:
        return
    await get_mcp_bridge()


async def stop_mcp_bridge() -> None:
    global _bridge
    async with _bridge_lock:
        if _bridge is not None:
            await _bridge.stop()
            _bridge = None


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    bridge = await get_mcp_bridge()
    return await bridge.call_tool(name, arguments)


def call_mcp_tool_sync(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Use from sync code only when no event loop is running (e.g. scripts)."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call_mcp_tool(name, arguments))

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, call_mcp_tool(name, arguments)).result()
