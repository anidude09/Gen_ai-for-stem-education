"""
region_detection.py

This module provides functionality to detect text inside a specific region 
of an uploaded image using OpenCV and Tesseract (via pytesseract).

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

import pytesseract
from pytesseract import Output
from .detect import detect_circles_with_text_from_image

# Configure Tesseract binary location.
DEFAULT_TESSERACT_CMD = r"C:\Users\aniruddh\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", DEFAULT_TESSERACT_CMD)
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Detection tuning parameters (should roughly match detect.py)
MIN_CONFIDENCE = 60.0
MIN_BOX_WIDTH = 10
MIN_BOX_HEIGHT = 10

# Initialize FastAPI router
router = APIRouter()


def _tess_image_to_data(img_bgr, psm: str = "6"):
    """
    Helper to run Tesseract's image_to_data on a BGR OpenCV image and
    return the parsed dictionary.
    """
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return pytesseract.image_to_data(
        img_rgb,
        lang="eng",
        config=f"--oem 3 --psm {psm}",
        output_type=Output.DICT,
    )


def _is_construction_text(text: str) -> bool:
    """
    Mirror of the heuristic used in detect.py to keep only construction-like text.
    """
    if not text:
        return False

    t = text.strip()
    if len(t) < 2:
        return False

    if not re.match(r"^[A-Za-z0-9.\-]+$", t):
        return False

    patterns = [
        r"^[A-Z]{3,}$",
        r"^[A-Z]+\d+(\.\d+)?$",
        r"^\d{2,4}$",
    ]
    for pat in patterns:
        if re.match(pat, t):
            return True

    if re.match(r"^[A-Za-z]{3,}$", t):
        return True

    return False


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

    # Text within the region
    data = _tess_image_to_data(crop, psm="6")

    # Group words into line-level boxes as in detect.py
    lines = {}
    n = len(data["text"])
    for i in range(n):
        raw_text = data["text"][i] or ""
        text = raw_text.strip()

        conf_str = data["conf"][i]
        try:
            conf = float(conf_str)
        except (ValueError, TypeError):
            conf = -1.0

        if conf < MIN_CONFIDENCE or not text:
            continue

        if not _is_construction_text(text):
            continue

        left = int(data["left"][i])
        top = int(data["top"][i])
        width = int(data["width"][i])
        height = int(data["height"][i])

        if width < MIN_BOX_WIDTH or height < MIN_BOX_HEIGHT:
            continue

        key = (data.get("block_num", [0])[i], data.get("line_num", [0])[i])
        if key not in lines:
            lines[key] = {
                "texts": [],
                "min_x": left,
                "min_y": top,
                "max_x": left + width,
                "max_y": top + height,
            }
        else:
            lines[key]["min_x"] = min(lines[key]["min_x"], left)
            lines[key]["min_y"] = min(lines[key]["min_y"], top)
            lines[key]["max_x"] = max(lines[key]["max_x"], left + width)
            lines[key]["max_y"] = max(lines[key]["max_y"], top + height)

        lines[key]["texts"].append(text)

    text_boxes = []
    for i, (_, line) in enumerate(lines.items(), start=1):
        combined_text = " ".join(line["texts"]).strip()
        if not combined_text:
            continue

        text_boxes.append(
            {
                "id": i,
                "x1": int(line["min_x"]) + x,
                "y1": int(line["min_y"]) + y,
                "x2": int(line["max_x"]) + x,
                "y2": int(line["max_y"]) + y,
                "text": combined_text,
            }
        )

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
