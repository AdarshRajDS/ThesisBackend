"""
Pre-upload diagnostics: verify Supabase / MinIO config without ingesting a PDF.
"""
from fastapi import APIRouter

from app.services.object_storage import storage_debug_snapshot

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/storage")
def debug_storage():
    """
    Check storage provider, import, client, bucket existence, and root file listing.
    Call this before POST /upload-pdf/ to verify Supabase is reachable.
    """
    return storage_debug_snapshot()
