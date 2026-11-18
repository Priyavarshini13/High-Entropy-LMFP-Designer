"""
Cloud Storage Helper for ECMT AI.

Provides unified private file storage:
1. Supabase Free Object Storage (Private 1GB cloud bucket with signed URLs & authenticated proxy).
2. Local Disk Fallback (Persistent local folder `data/uploads/` for local desktop / development runs).
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "ecmt-uploads")


def is_supabase_storage_configured() -> bool:
    """Return True if Supabase storage credentials are configured in environment."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_storage_status() -> Dict[str, Any]:
    """Return current storage backend status and metadata."""
    if is_supabase_storage_configured():
        return {
            "mode": "supabase_object_storage",
            "provider": "Supabase Storage (Free Tier, 1GB quota)",
            "bucket": SUPABASE_BUCKET,
            "is_private": True,
            "access_control": "signed_url_and_backend_authorization",
            "persistent_cloud": True,
            "supabase_url": SUPABASE_URL,
        }
    return {
        "mode": "local_disk",
        "provider": "Local Disk Storage (data/uploads)",
        "bucket": "local",
        "is_private": True,
        "access_control": "backend_session_authorization",
        "persistent_cloud": False,
        "local_path": str(LOCAL_UPLOAD_DIR),
    }


def ensure_supabase_bucket_exists() -> bool:
    """Check if the Supabase storage bucket exists; if not, create it as a PRIVATE bucket."""
    if not is_supabase_storage_configured():
        return False

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    check_url = f"{SUPABASE_URL}/storage/v1/bucket/{SUPABASE_BUCKET}"

    try:
        res = requests.get(check_url, headers=headers, timeout=5)
        if res.status_code == 200:
            return True

        # Bucket does not exist: create strictly PRIVATE bucket (public: False)
        create_url = f"{SUPABASE_URL}/storage/v1/bucket"
        payload = {
            "id": SUPABASE_BUCKET,
            "name": SUPABASE_BUCKET,
            "public": False,  # Strict private access
            "file_size_limit": 26214400,  # 25MB
            "allowed_mime_types": [
                "image/png", "image/jpeg", "image/webp", "image/tiff",
                "application/pdf", "text/csv", "application/json"
            ],
        }
        res_create = requests.post(create_url, headers=headers, json=payload, timeout=5)
        return res_create.status_code in (200, 201)
    except Exception:
        return False


def generate_signed_url(clean_path: str, expires_in_seconds: int = 86400) -> Optional[str]:
    """
    Generate an authenticated signed URL for a private file in the Supabase bucket.
    Default validity: 24 hours (86,400 seconds).
    """
    if not is_supabase_storage_configured():
        return None

    clean_path = clean_path.replace("\\", "/").lstrip("/")
    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{SUPABASE_BUCKET}/{clean_path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"expiresIn": expires_in_seconds}

    try:
        res = requests.post(sign_url, headers=headers, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            raw_signed = data.get("signedURL")
            if raw_signed:
                if raw_signed.startswith("http"):
                    return raw_signed
                return f"{SUPABASE_URL}{raw_signed}"
    except Exception:
        pass

    return None


def fetch_file_bytes(clean_path: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Retrieve file binary content and content-type, checking local storage first,
    then downloading from private Supabase bucket via authenticated API.
    """
    clean_path = clean_path.replace("\\", "/").lstrip("/")

    # Check local disk first
    local_target = LOCAL_UPLOAD_DIR / clean_path
    if local_target.exists() and local_target.is_file():
        try:
            content = local_target.read_bytes()
            guessed_type, _ = mimetypes.guess_type(str(local_target))
            return content, (guessed_type or "application/octet-stream")
        except Exception:
            pass

    # Retrieve from Supabase Private Bucket using service credentials
    if is_supabase_storage_configured():
        try:
            download_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{clean_path}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
            res = requests.get(download_url, headers=headers, timeout=10)
            if res.status_code == 200:
                c_type = res.headers.get("content-type") or mimetypes.guess_type(clean_path)[0] or "application/octet-stream"
                return res.content, c_type
        except Exception:
            pass

    return None, None


def save_file(
    content: bytes,
    relative_path: str,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save file content to private cloud storage (Supabase) if configured,
    or fallback to local disk storage (`data/uploads`).

    Enforces private storage: returns backend-authenticated authorization URL
    and signed Supabase URL.
    """
    local_target = LOCAL_UPLOAD_DIR / relative_path
    local_target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(local_target, "wb") as f:
            f.write(content)
    except Exception:
        pass

    clean_path = relative_path.replace("\\", "/").lstrip("/")

    if not content_type:
        guessed_type, _ = mimetypes.guess_type(clean_path)
        content_type = guessed_type or "application/octet-stream"

    # Attempt Supabase Private Cloud Upload if configured
    signed_url = None
    if is_supabase_storage_configured():
        try:
            ensure_supabase_bucket_exists()

            upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{clean_path}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            }
            res = requests.post(upload_url, headers=headers, data=content, timeout=10)

            if res.status_code in (200, 201):
                # Generate 24-hour authenticated signed URL for private access
                signed_url = generate_signed_url(clean_path, expires_in_seconds=86400)
                return {
                    "url": signed_url or f"/api/storage/file/{clean_path}",
                    "signed_url": signed_url,
                    "auth_proxy_url": f"/api/storage/file/{clean_path}",
                    "storage_mode": "supabase_private",
                    "filename": Path(clean_path).name,
                    "relative_path": clean_path,
                    "size_bytes": len(content),
                    "content_type": content_type,
                    "persistent_cloud": True,
                    "is_private": True,
                }
        except Exception:
            pass

    # Local fallback URL with authenticated proxy
    return {
        "url": f"/api/storage/file/{clean_path}",
        "auth_proxy_url": f"/api/storage/file/{clean_path}",
        "storage_mode": "local_private",
        "filename": Path(clean_path).name,
        "relative_path": clean_path,
        "size_bytes": len(content),
        "content_type": content_type,
        "persistent_cloud": False,
        "is_private": True,
    }
