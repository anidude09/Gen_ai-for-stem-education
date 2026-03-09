"""
regions_detect.py

Detect text inside a specific region of an uploaded image using
PaddleOCR (GPU) and the packaged circle detection pipeline.
"""

from fastapi import APIRouter, File, UploadFile, Form
import cv2
import numpy as np
import base64

from construction_ocr.pipeline import detect_text
from construction_circle_detector.pipeline import detect_circles

router = APIRouter()


def detect_text_in_region(img, region):
    """
    Detect text and circles within a specified rectangular region.

    Args:
        img: Full OpenCV BGR image.
        region: (x, y, w, h) tuple for the region of interest.

    Returns:
        (circle_boxes, text_boxes, crop_base64)
    """
    x, y, w, h = region
    crop = img[y:y + h, x:x + w]

    # 1) Circles within the region, offset back to original coords
    regional_circles = detect_circles(crop)
    circle_boxes = []
    for c in regional_circles:
        circle_boxes.append({
            **c,
            "x": int(c["x"]) + x,
            "y": int(c["y"]) + y,
        })

    # 2) Text within the region (PaddleOCR), offset back to original
    regional_texts = detect_text(crop)
    text_boxes = []
    for t in regional_texts:
        text_boxes.append({
            **t,
            "x1": int(t["x1"]) + x,
            "y1": int(t["y1"]) + y,
            "x2": int(t["x2"]) + x,
            "y2": int(t["y2"]) + y,
        })

    # 3) Cropped region as base64 for frontend display
    _, buffer = cv2.imencode(".jpg", crop)
    crop_base64 = base64.b64encode(buffer).decode("utf-8")

    return circle_boxes, text_boxes, crop_base64


@router.post("/region-detect")
async def detect_in_region(
    file: UploadFile = File(...),
    x: int = Form(...),
    y: int = Form(...),
    w: int = Form(...),
    h: int = Form(...),
):
    """
    FastAPI endpoint to detect text within a user-specified region.
    Returns: { circles: [...], detections: [...], cropped_image: "..." }
    """
    image_bytes = await file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    circles, detections, crop_base64 = detect_text_in_region(img, (x, y, w, h))
    return {
        "circles": circles,
        "detections": detections,
        "cropped_image": f"data:image/jpeg;base64,{crop_base64}",
    }
