from pydantic import BaseModel
from typing import Literal, Optional, List


class GenerateBrain3DRequest(BaseModel):
    prompt: str
    quality: Literal["draft", "standard", "high"] = "standard"
    format: Literal["glb", "gltf"] = "glb"
    include_preview: bool = True


class GenerateBrain3DResponse(BaseModel):
    status: str
    asset_url: Optional[str] = None
    preview_url: Optional[str] = None
    task_id: Optional[str] = None
    warnings: Optional[List[str]] = None
    error: Optional[str] = None
