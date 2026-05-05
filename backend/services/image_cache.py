"""
image_cache.py — In-memory image byte cache and disk resolver for server-hosted images.

Avoids re-uploading images that the backend already has (e.g. /images/*.png pages).
Cache key: "{page_session_id}:{page_label}"
"""

from __future__ import annotations

import os

_cache: dict[str, bytes] = {}

# Resolve the images directory served at /images/
# __file__ is backend/services/image_cache.py → three dirname calls reach the project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IMAGES_DIR = os.path.normpath(os.path.join(_PROJECT_ROOT, "app", "dist", "images"))
print(f"[image_cache] Images dir: {_IMAGES_DIR} (exists={os.path.isdir(_IMAGES_DIR)})")


def cache_key(page_session_id: str, page_label: str = "") -> str:
    return f"{page_session_id}:{page_label}"


def store(key: str, data: bytes) -> None:
    _cache[key] = data


def get(key: str) -> bytes | None:
    return _cache.get(key)


def resolve_server_path(server_path: str) -> bytes | None:
    """
    Given a URL path like /images/A5.1.png, read the bytes from disk.
    Returns None if the path doesn't map to a known directory or the file doesn't exist.
    """
    if not server_path:
        return None
    # Normalise: strip query string and fragment
    server_path = server_path.split("?")[0].split("#")[0]
    if server_path.startswith("/images/"):
        filename = server_path[len("/images/"):]
        disk_path = os.path.normpath(os.path.join(_IMAGES_DIR, filename))
        # Guard against path traversal
        if not disk_path.startswith(_IMAGES_DIR):
            return None
        if os.path.isfile(disk_path):
            with open(disk_path, "rb") as f:
                return f.read()
    return None
