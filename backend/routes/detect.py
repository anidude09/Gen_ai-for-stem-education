"""
detect.py

OCR & Circle Detection route. Uses packaged:
- construction_circle_detector
- construction_ocr
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form
from construction_circle_detector import detect_circles_from_bytes
from construction_ocr.pipeline import detect_text_from_bytes
from services.image_cache import store as img_store, get as img_get, cache_key, resolve_server_path

router = APIRouter()

@router.post("/")
async def detect_route(
    file: Optional[UploadFile] = File(None),
    circles_only: bool = Form(False),
    page_session_id: Optional[str] = Form(None),
    page_label: str = Form(""),
    server_image_path: Optional[str] = Form(None),
):
    """
    Detect circles and text from an image.

    Priority for image source:
    1. Cache (if page_session_id + page_label provided and context was already built)
    2. server_image_path (backend reads /images/*.png directly from disk — no upload needed)
    3. Uploaded file (fallback)
    """
    try:
        image_bytes = None

        # 1. Cache hit
        if page_session_id is not None:
            image_bytes = img_get(cache_key(page_session_id, page_label))
            if image_bytes:
                print(f"[detect] Cache hit for session={page_session_id[:8]} label={page_label!r}")

        # 2. Server-side disk read
        if image_bytes is None and server_image_path:
            image_bytes = resolve_server_path(server_image_path)
            if image_bytes:
                print(f"[detect] Read {len(image_bytes)//1024}KB from disk: {server_image_path}")
                if page_session_id:
                    img_store(cache_key(page_session_id, page_label), image_bytes)

        # 3. Uploaded file
        if image_bytes is None:
            if file is None:
                return {"error": "No image provided", "circles": [], "texts": []}
            image_bytes = await file.read()
            if page_session_id:
                img_store(cache_key(page_session_id, page_label), image_bytes)

        if circles_only:
            circles = await asyncio.to_thread(detect_circles_from_bytes, image_bytes)
            texts = []
        else:
            circles_task = asyncio.to_thread(detect_circles_from_bytes, image_bytes)
            texts_task   = asyncio.to_thread(detect_text_from_bytes, image_bytes)
            circles, texts = await asyncio.gather(circles_task, texts_task)

        return {
            "circles": circles,
            "texts": texts
        }

    except Exception as e:
        print(f"[detect route] Endpoint error: {e}")
        return {"error": str(e), "circles": [], "texts": []}
