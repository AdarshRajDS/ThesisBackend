"""
Storage abstraction for serving RAG images in production.
Supports MinIO (S3-compatible) and Supabase Storage.
When storage is disabled/unavailable, the RAG chain falls back to local /outputs.
"""
import io
from datetime import timedelta
from typing import Any, Optional

from src.config.settings import settings


def _using_supabase() -> bool:
    return getattr(settings, "storage_provider", "minio").lower() == "supabase"


def get_active_bucket_name() -> str:
    """Bucket name for metadata / logging (matches active provider)."""
    if _using_supabase():
        return settings.supabase_bucket
    return settings.minio_bucket


def _minio_client():
    if not getattr(settings, "minio_enabled", True):
        print("MinIO disabled")
        return None
    try:
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        print("MinIO client created:", settings.minio_endpoint)
        return client
    except Exception as e:
        print("MinIO client creation error:", e)
        return None


def _supabase_client():
    url = getattr(settings, "supabase_url", "")
    key = getattr(settings, "supabase_service_role_key", "")

    if not url or not key:
        print("Supabase config missing (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)")
        return None

    try:
        from supabase import create_client

        return create_client(url, key)
    except Exception as e:
        print("Supabase client creation error:", e)
        return None

def _bucket_name_from_item(bucket: Any) -> Optional[str]:
    if isinstance(bucket, dict):
        return bucket.get("name")
    name = getattr(bucket, "name", None)
    if isinstance(name, str):
        return name
    return None


def ensure_bucket() -> bool:
    """Ensure storage bucket is usable for the active provider."""
    if _using_supabase():
        # Supabase bucket is expected to be pre-created in dashboard.
        client = _supabase_client()
        if not client:
            return False
        try:
            buckets = client.storage.list_buckets() or []
            names = []
            for b in buckets:
                n = _bucket_name_from_item(b)
                if n:
                    names.append(n)
            return settings.supabase_bucket in names
        except Exception as e:
            print("Supabase bucket check error:", e)
            return False

    client = _minio_client()
    if not client:
        return False
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        return True
    except Exception:
        return False


def put_object(object_key: str, data: bytes, content_type: str = "image/png") -> bool:
    if _using_supabase():
        client = _supabase_client()
        if not client:
            return False
        try:
            # Supabase requires raw bytes (NOT BytesIO)
            safe_key = object_key.replace("\\", "/")

            file_options = {
                "content-type": content_type,
                "upsert": "true",
            }

            client.storage.from_(settings.supabase_bucket).upload(
                safe_key,
                data,   # ✅ pass raw bytes directly
                file_options,
            )

            print("Uploaded to Supabase:", safe_key)
            return True

        except Exception as e:
            print("SUPABASE UPLOAD ERROR:", e)
            return False

    client = _minio_client()
    if not client:
        print("MinIO client is None")
        return False
    try:
        ensure_bucket()
        client.put_object(
            settings.minio_bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        print("Uploaded:", object_key)
        return True
    except Exception as e:
        print("UPLOAD ERROR:", e)
        return False

def _extract_supabase_signed_url(signed: Any) -> Optional[str]:
    """Parse create_signed_url / SDK responses into a full HTTPS URL."""
    if signed is None:
        return None
    if isinstance(signed, str) and signed.startswith("http"):
        return signed
    if not isinstance(signed, dict):
        return None
    url = (
        signed.get("signedURL")
        or signed.get("signedUrl")
        or signed.get("signed_url")
    )
    if isinstance(url, dict):
        url = url.get("signedURL") or url.get("signedUrl")
    if not url or not isinstance(url, str):
        return None
    if url.startswith("http"):
        return url
    base = (settings.supabase_url or "").rstrip("/")
    if not base:
        return None
    return f"{base}{url}" if url.startswith("/") else f"{base}/{url}"


def get_presigned_url(object_key: str, expire_seconds: Optional[int] = None) -> Optional[str]:
    if _using_supabase():
        client = _supabase_client()
        if not client:
            return None
        try:
            expire = expire_seconds or getattr(
                settings, "supabase_signed_url_expire_seconds", 3600
            )
            safe_key = object_key.replace("\\", "/")
            signed = client.storage.from_(settings.supabase_bucket).create_signed_url(
                path=safe_key,
                expires_in=int(expire),
            )
            # Some SDK versions wrap payload (e.g. APIResponse with .data)
            payload = signed
            if hasattr(signed, "data") and signed.data is not None:
                payload = signed.data
            out = _extract_supabase_signed_url(payload)
            if out:
                return out
            print("SUPABASE PRESIGN: unexpected response shape:", type(signed), signed)
            return None
        except Exception as e:
            print("SUPABASE PRESIGN ERROR:", e)
            return None

    client = _minio_client()
    if not client:
        return None

    try:
        expire = expire_seconds or getattr(
            settings, "minio_presign_expire_seconds", 3600
        )
        expire_delta = timedelta(seconds=int(expire))
        return client.presigned_get_object(
            settings.minio_bucket,
            object_key,
            expires=expire_delta,
        )
    except Exception as e:
        print("PRESIGN ERROR:", e)
        return None

def is_available() -> bool:
    """True if active storage provider is configured and reachable."""
    return ensure_bucket()


def storage_debug_snapshot() -> dict:
    """
    Diagnostics for GET /debug/storage and upload pipeline.
    Does not expose secrets — only booleans and masked URL host.
    """
    from urllib.parse import urlparse

    out: dict = {
        "storage_provider": getattr(settings, "storage_provider", "minio"),
        "using_supabase": _using_supabase(),
        "supabase_url_configured": bool((settings.supabase_url or "").strip()),
        "supabase_key_configured": bool((settings.supabase_service_role_key or "").strip()),
        "supabase_url_host": None,
        "supabase_import_ok": False,
        "supabase_import_error": None,
        "supabase_client_ok": False,
        "supabase_bucket": settings.supabase_bucket,
        "bucket_exists_in_project": None,
        "bucket_list_error": None,
        "sample_object_keys": [],
        "minio_enabled": settings.minio_enabled,
    }

    url = (settings.supabase_url or "").strip()
    if url:
        try:
            parsed = urlparse(url)
            out["supabase_url_host"] = parsed.netloc or None
        except Exception:
            out["supabase_url_host"] = "(invalid URL)"

    try:
        import supabase as _sb  # noqa: F401

        out["supabase_import_ok"] = True
    except ImportError as e:
        out["supabase_import_error"] = str(e)
        return out

    if not _using_supabase():
        out["note"] = "Active provider is minio; Supabase checks skipped."
        return out

    client = _supabase_client()
    if not client:
        out["supabase_client_ok"] = False
        return out

    out["supabase_client_ok"] = True

    try:
        buckets = client.storage.list_buckets() or []
        names = []
        for b in buckets:
            n = _bucket_name_from_item(b)
            if n:
                names.append(n)
        out["bucket_names_in_project"] = names
        out["bucket_exists_in_project"] = settings.supabase_bucket in names
    except Exception as e:
        out["bucket_list_error"] = str(e)

    try:
        bucket_api = client.storage.from_(settings.supabase_bucket)
        listed = bucket_api.list() if hasattr(bucket_api, "list") else []
        # Flatten first-level prefixes / files for visibility
        keys = []
        if isinstance(listed, list):
            for item in listed[:10]:
                if isinstance(item, dict) and item.get("name"):
                    keys.append(item["name"])
        out["sample_object_keys"] = keys
        out["bucket_list_prefix_root_count"] = len(listed) if isinstance(listed, list) else None
    except Exception as e:
        out["bucket_list_files_error"] = str(e)

    return out
