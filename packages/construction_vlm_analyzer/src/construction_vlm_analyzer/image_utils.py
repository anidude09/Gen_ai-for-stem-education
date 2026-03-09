"""
image_utils.py — Image resizing and base64 encoding for GPT-4o limitations.
"""

from __future__ import annotations

import base64
import io
from PIL import Image

# GPT-4o high-detail mode optimal max size to avoid wasting tokens on empty padding
MAX_LONG_SIDE = 2048


def resize_for_vlm(img: Image.Image) -> Image.Image:
    """
    Resize image so its longest side is at most MAX_LONG_SIDE pixels.
    Preserves aspect ratio. Returns the image unchanged if already small enough.
    """
    w, h = img.size
    long_side = max(w, h)
    if long_side <= MAX_LONG_SIDE:
        return img
    scale = MAX_LONG_SIDE / long_side
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    print(f"[vlm_analyzer] Resizing {w}x{h} → {new_w}x{new_h} for GPT-4o Vision")
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def encode_image(img: Image.Image) -> str:
    """Encode a PIL Image to PNG base64 string."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
