from fastapi import APIRouter
from app.schemas.visualize import VisualizeRequest, VisualizeResponse
from app.services.visualization_service import visualize

router = APIRouter(prefix="/visualize", tags=["Visualization"])


@router.post("/", response_model=VisualizeResponse)
def run_visualize(req: VisualizeRequest):
    return visualize(req.question)
