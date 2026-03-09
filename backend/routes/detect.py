"""
detect.py

OCR & Circle Detection route. Uses packaged:
- construction_circle_detector
- construction_ocr
"""

import asyncio
from fastapi import APIRouter, File, UploadFile, Form
from construction_circle_detector import detect_circles_from_bytes
from construction_ocr.pipeline import detect_text_from_bytes

router = APIRouter()

@router.post("/")
async def detect_route(file: UploadFile = File(...), circles_only: bool = Form(False)):
    """
    FastAPI endpoint to detect circles and text from an uploaded image.
    Returns: { circles: [...], texts: [...] }
    """
    try:
        image_bytes = await file.read()

        if circles_only:
            circles = await asyncio.to_thread(detect_circles_from_bytes, image_bytes)
            texts = []
        else:
            # Run both pipelines concurrently using thread pool natively inside packages
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
