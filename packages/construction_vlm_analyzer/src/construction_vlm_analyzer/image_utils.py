"""
image_utils.py — Image resizing and base64 encoding for GPT-4o limitations.
"""

from __future__ import annotations

import base64
import io
from PIL import Image

# Default GPT-4o high-detail max size (callers can override)
MAX_LONG_SIDE = 2048


def resize_for_vlm(img: Image.Image, max_long_side: int = MAX_LONG_SIDE) -> Image.Image:
    """
    Resize image so its longest side is at most max_long_side pixels.
    Preserves aspect ratio. Returns the image unchanged if already small enough.
    """
    w, h = img.size
    long_side = max(w, h)
    if long_side <= max_long_side:
        return img
    scale = max_long_side / long_side
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    print(f"[vlm_analyzer] Resizing {w}x{h} → {new_w}x{new_h} for GPT-4o Vision")
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def encode_image(img: Image.Image, fmt: str = "PNG") -> tuple[str, str]:
    """
    Encode a PIL Image to base64 string.
    Returns (base64_str, mime_type).
    fmt: "PNG" or "JPEG"
    """
    fmt = fmt.upper()
    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=85 if fmt == "JPEG" else None)
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    return base64.b64encode(buf.getvalue()).decode("utf-8"), mime
