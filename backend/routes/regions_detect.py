"""
region_detection.py

This module provides functionality to detect text inside a specific region 
of an uploaded image using OpenCV and EasyOCR (GPU preferred, CPU fallback).

Key functionalities:
- Extract a specified rectangular region from an image.
- Perform OCR (Optical Character Recognition) on the cropped region.
- Return detected text boxes along with their coordinates.
- Return the cropped region as a base64-encoded image.
"""

from fastapi import APIRouter, File, UploadFile, Form
import cv2
import numpy as np
import base64
import os
import re

from .detect import (
    detect_circles_with_text_from_image,
    _EASYOCR_READER,
    _preprocess_for_easyocr,
    _run_easyocr,
    _is_construction_text,
    _clean_text,
    _unpack_easyocr_line,
    EASYOCR_MIN_CONFIDENCE,
    MIN_BOX_WIDTH,
    MIN_BOX_HEIGHT,
    EASYOCR_PARAMS,
)

# Initialize FastAPI router
router = APIRouter()


def detect_text_in_region(img, region):
    """
    Detects text within a specified rectangular region of an image.

    Steps:
    1. Crop the region of interest (ROI) from the original image.
    2. Run Tesseract to detect text inside the cropped region.
    3. Adjust bounding box coordinates relative to the original image.
    4. Convert the cropped region to base64 for return.

    Args:
        img (numpy.ndarray): The original OpenCV image.
        region (tuple): A tuple (x, y, w, h) specifying the top-left 
                        coordinates, width, and height of the region.

    Returns:
        tuple:
            - circle_boxes (list of dict): Circles detected in the region, with
              coordinates mapped back to the original image.
            - text_boxes (list of dict): Each dict contains:
                - id (int): Box index
                - x1, y1 (int): Top-left coordinates
                - x2, y2 (int): Bottom-right coordinates
                - text (str): Detected text
            - crop_base64 (str): Base64-encoded cropped image.
    """
    x, y, w, h = region
    crop = img[y:y + h, x:x + w]

    # Circles within the region (relative to crop), then offset by (x, y)
    regional_circles = detect_circles_with_text_from_image(crop)
    circle_boxes = []
    for c in regional_circles:
        circle_boxes.append(
            {
                **c,
                "x": int(c["x"]) + x,
                "y": int(c["y"]) + y,
            }
        )

    # Text within the region (EasyOCR) with blueprint cleanup
    text_boxes = []
    if _EASYOCR_READER is None:
        print("EasyOCR reader not initialized; cannot perform regional text detection")
    else:
        crop_proc = _preprocess_for_easyocr(crop)
        try:
            crop_rgb = cv2.cvtColor(crop_proc, cv2.COLOR_BGR2RGB)
        except Exception:
            crop_rgb = crop_proc

        ocr_results = _run_easyocr(crop_rgb, EASYOCR_PARAMS)

        idx = 1
        for line in ocr_results:
            try:
                bbox, text, conf = _unpack_easyocr_line(line)

                if not text or bbox is None:
                    continue
                if conf is not None and conf < EASYOCR_MIN_CONFIDENCE:
                    continue

                t = _clean_text(text)
                if len(t) < 2:
                    continue

                if not _is_construction_text(t):
                    continue

                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)

                width = max_x - min_x
                height = max_y - min_y

                if width < MIN_BOX_WIDTH or height < MIN_BOX_HEIGHT:
                    continue

                text_boxes.append(
                    {
                        "id": idx,
                        "x1": int(min_x) + x,
                        "y1": int(min_y) + y,
                        "x2": int(max_x) + x,
                        "y2": int(max_y) + y,
                        "text": t,
                    }
                )
                idx += 1
            except Exception as e:
                print(f"Error processing EasyOCR region text box: {e}")
                continue

    # Convert cropped region to base64 string
    _, buffer = cv2.imencode(".jpg", crop)
    crop_base64 = base64.b64encode(buffer).decode("utf-8")

    return circle_boxes, text_boxes, crop_base64


@router.post("/region-detect")
async def detect_in_region(
    file: UploadFile = File(...),
    x: int = Form(...),
    y: int = Form(...),
    w: int = Form(...),
    h: int = Form(...)
):
    """
    FastAPI endpoint to detect text within a user-specified region of an uploaded image.

    Steps:
    1. Accepts an image file and region coordinates (x, y, w, h).
    2. Decodes the image into an OpenCV format.
    3. Calls `detect_text_in_region` to extract text and crop region.
    4. Returns:
        - Detected text boxes with coordinates and recognized text.
        - Cropped image region as a base64 string.

    
    """
    image_bytes = await file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    circles, detections, crop_base64 = detect_text_in_region(img, (x, y, w, h))
    return {
        "circles": circles,
        "detections": detections,
        "cropped_image": f"data:image/jpeg;base64,{crop_base64}"
    }
