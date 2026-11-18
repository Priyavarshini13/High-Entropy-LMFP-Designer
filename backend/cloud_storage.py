"""
Cloud Storage Helper for ECMT AI.

Provides unified file storage:
1. Supabase Free Object Storage (Persistent 1GB cloud bucket for Render/Vercel zero-cost deployment).
2. Local Disk Fallback (Persistent local folder `data/uploads/` for local desktop / development runs).
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional
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
            "persistent_cloud": True,
            "supabase_url": SUPABASE_URL,
        }
    return {
        "mode": "local_disk",
        "provider": "Local Disk Storage (data/uploads)",
        "bucket": "local",
        "persistent_cloud": False,
        "local_path": str(LOCAL_UPLOAD_DIR),
    }


def ensure_supabase_bucket_exists() -> bool:
    """Check if the Supabase storage bucket exists; if not, create it as a public bucket."""
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

        # Bucket does not exist, attempt to create public bucket
        create_url = f"{SUPABASE_URL}/storage/v1/bucket"
        payload = {
            "id": SUPABASE_BUCKET,
            "name": SUPABASE_BUCKET,
            "public": True,
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


def save_file(
    content: bytes,
    relative_path: str,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save file content to persistent cloud storage (Supabase) if configured,
    or fallback to local disk storage (`data/uploads`).

    Args:
        content: Binary bytes of the uploaded file.
        relative_path: Subpath e.g. 'images/my_photo.png' or 'literature/paper.pdf'.
        content_type: MIME type of the file.

    Returns:
        Dict with public URL, storage mode, filename, and size.
    """
    # Always keep local copy if possible (for local caching or fallback)
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

    # Attempt Supabase Cloud Upload if configured
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
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{clean_path}"
                return {
                    "url": public_url,
                    "storage_mode": "supabase",
                    "filename": Path(clean_path).name,
                    "relative_path": clean_path,
                    "size_bytes": len(content),
                    "content_type": content_type,
                    "persistent_cloud": True,
                }
        except Exception:
            # Fall back to local URL if Supabase network call fails
            pass

    # Local fallback URL
    return {
        "url": f"/uploads/{clean_path}",
        "storage_mode": "local",
        "filename": Path(clean_path).name,
        "relative_path": clean_path,
        "size_bytes": len(content),
        "content_type": content_type,
        "persistent_cloud": False,
    }
