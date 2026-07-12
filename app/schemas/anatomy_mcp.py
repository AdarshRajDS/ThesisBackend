from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


class AnatomyExportRequest(BaseModel):
    part_query: str = Field(min_length=1, max_length=80)
    include_preview: bool = True
    region_hint: Optional[str] = Field(default=None, max_length=80)


class AnatomySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=80)
    limit: int = Field(default=10, ge=1, le=50)


class AnatomySuggestRequest(BaseModel):
    query: str = Field(min_length=1, max_length=80)
    limit: int = Field(default=8, ge=1, le=20)
    include_nearby: bool = True


class AnatomySuggestionItem(BaseModel):
    label: str
    catalog_id: Optional[str] = None
    match_type: Optional[str] = None
    object_count: Optional[int] = None
    estimated_complexity: Optional[str] = None
    side: Optional[str] = None
    match_reason: Optional[str] = None
    confidence: Optional[float] = None
    can_export: bool = True
    export_probe: Optional[str] = None
    parent_collections: Optional[List[str]] = None
    matched_tokens: Optional[List[str]] = None


class AnatomySuggestResult(BaseModel):
    status: str
    query: str
    catalog_query: Optional[str] = None
    normalized_query: Optional[str] = None
    catalog_name: Optional[str] = None
    catalog_path: Optional[str] = None
    resolver_status: Optional[str] = None
    suggestions: List[AnatomySuggestionItem] = Field(default_factory=list)
    suggestion_labels: List[str] = Field(default_factory=list)
    auto_export_candidate: Optional[AnatomySuggestionItem] = None
    auto_export_threshold: Optional[float] = None
    error: Optional[str] = None
    instruction: Optional[str] = None


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
    suggestions: Optional[List[AnatomySuggestionItem]] = None
    suggestion_labels: Optional[List[str]] = None


class AnatomySearchResult(BaseModel):
    query: str
    result_count: int = 0
    results: List[dict] = Field(default_factory=list)
    suggestions: List[AnatomySuggestionItem] = Field(default_factory=list)
    suggestion_labels: List[str] = Field(default_factory=list)
    resolver_status: Optional[str] = None
    catalog_name: Optional[str] = None
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
    catalog_suggestions: List[AnatomySuggestionItem] = Field(default_factory=list)
    suggestion_labels: List[str] = Field(default_factory=list)
    error: Optional[str] = None
