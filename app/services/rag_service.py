from src.multimodal.run_multimodal_rag import run_multimodal_rag
from app.services.blender_service import render_related_anatomy


def ask_question(question: str):

    result = run_multimodal_rag(question)
    render = render_related_anatomy(
        question=question,
        answer=result.get("answer", ""),
        sources=result.get("sources") or [],
    )

    return {
        "answer": result["answer"],
        "images": result.get("images", []),
        "sources": result.get("sources"),
        "grounding": result.get("grounding"),
        "render_3d_url": render.get("render_3d_url"),
        "render_3d_model_url": render.get("render_3d_model_url"),
        "render_3d_anatomy": render.get("anatomy_key"),
    }
