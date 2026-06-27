from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


class AnatomyExportRequest(BaseModel):
    part_query: str = Field(min_length=1, max_length=80)
    include_preview: bool = True
    region_hint: Optional[str] = Field(default=None, max_length=80)


class AnatomySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=80)
    limit: int = Field(default=10, ge=1, le=50)


class AnatomyExportResult(BaseModel):
    status: str
    part_query: Optional[str] = None
    part_label: Optional[str] = None
    model_url: Optional[str] = None
    annotations_url: Optional[str] = None
    viewer_url: Optional[str] = None
    preview_url: Optional[str] = None
    source_blend: Optional[str] = None
    selected_objects: Optional[List[str]] = None
    annotation_labels: Optional[List[str]] = None
    annotation_count: Optional[int] = None
    cache_hit: Optional[bool] = None
    error: Optional[str] = None
    matches: Optional[List[str]] = None
    instruction: Optional[str] = None


class AnatomySearchResult(BaseModel):
    query: str
    result_count: int = 0
    results: List[dict] = Field(default_factory=list)
    error: Optional[str] = None


class AnatomyAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    language: Literal["en", "de"] = "en"


class McpToolStep(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class CatalogInfo(BaseModel):
    catalog_name: Optional[str] = None
    catalog_path: Optional[str] = None
    catalog_description: Optional[str] = None
    source_blend: Optional[str] = None
    resolver_source: Optional[str] = None


class AnatomyAskResult(BaseModel):
    answer: str
    anatomy_export: Optional[AnatomyExportResult] = None
    mcp_tools_used: List[str] = Field(default_factory=list)
    mcp_tool_steps: List[McpToolStep] = Field(default_factory=list)
    mcp_mode: str = "lmstudio_mcp"
    catalog_info: Optional[CatalogInfo] = None
    error: Optional[str] = None
