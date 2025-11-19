"""
detect.py

This module defines image-processing routes and functions for detecting circles and text 
from uploaded images using OpenCV and Tesseract (via pytesseract).

Key functionalities:
- Detect circular regions in an image and extract text inside/near them.
- Detect textual regions across the entire image (excluding numeric-only text and quotes).
- Provide a FastAPI endpoint (`POST /`) that accepts an image file and returns 
  detected circles with text plus extracted non-numeric text regions.
"""

from fastapi import APIRouter, File, UploadFile
import cv2
import numpy as np
import re
import os

import pytesseract
from pytesseract import Output

# EasyOCR is used specifically for tiny circle callout text, where it tends
# to outperform Tesseract. If it's not installed, we fall back to Tesseract.
try:
    import easyocr  # type: ignore

    _EASYOCR_READER = easyocr.Reader(["en"], gpu=False)
except Exception:
    _EASYOCR_READER = None

# Configure Tesseract binary location.
# Prefer environment variable for portability; fall back to your known local path.
DEFAULT_TESSERACT_CMD = r"C:\Users\aniruddh\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", DEFAULT_TESSERACT_CMD)
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Detection tuning parameters (can be adjusted if needed)
MIN_CONFIDENCE = 60.0  # minimum Tesseract confidence to keep a box
MIN_BOX_WIDTH = 10     # ignore very tiny boxes (pixels)
MIN_BOX_HEIGHT = 10
EASYOCR_MIN_CONFIDENCE = 0.3  # EasyOCR confidence threshold for circle text

# Initialize FastAPI router for detection-related endpoints
router = APIRouter()


def _tess_image_to_data(img_bgr, psm: str = "6", extra_config: str = ""):
    """
    Helper to run Tesseract's image_to_data on a BGR OpenCV image and
    return the parsed dictionary.
    """
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    config = f"--oem 3 --psm {psm}"
    if extra_config:
        config = f"{config} {extra_config}"
    return pytesseract.image_to_data(
        img_rgb,
        lang="eng",
        config=config,
        output_type=Output.DICT,
    )


def _is_construction_text(text: str) -> bool:
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


def _normalize_page_candidate(raw: str) -> str | None:
    """Best-effort normalization of tokens like A9.1 / A9-1 / A91 -> A9.1."""
    if not raw:
        return None
    t = raw.strip().upper()
    # keep only letters, digits, dot, dash
    t = re.sub(r"[^A-Z0-9.\-]", "", t)
    if len(t) < 2:
        return None
    if not (re.search(r"[A-Z]", t) and re.search(r"\d", t)):
        return None
    t = t.replace("-", ".")
    parts = t.split(".")
    if len(parts) == 1:
        head = parts[0]
        if len(head) >= 3 and head[0].isalpha() and head[1:].isdigit():
            return head[:-1] + "." + head[-1]
        return head
    if len(parts) >= 2:
        left, right = parts[0], re.sub(r"\D", "", parts[1])
        if not right:
            return None

        # Heuristic cleanup for noisy sheet numbers like A83.2 -> A3.2.
        # We assume sheet indices are typically 1–9; if the numeric part
        # before the dot is > 9, progressively drop leading digits until
        # it falls into that range.
        m = re.match(r"^([A-Z]+)(\d+)$", left)
        if m:
            prefix, num_part = m.group(1), m.group(2)
            if num_part.isdigit():
                try:
                    n = int(num_part)
                    while len(num_part) > 1 and n > 9:
                        num_part = num_part[1:]
                        n = int(num_part)
                    left = prefix + num_part
                except ValueError:
                    pass

        return f"{left}.{right}"
    return None


def _extract_page_and_circle(
    page_texts: list[str] | None, circle_texts: list[str] | None
) -> tuple[str, str]:
    """
    Given two sets of OCR tokens from a circle:
    - page_texts: tokens from the *bottom* half of the circle (page number like A5.1)
    - circle_texts: tokens from the *top* half of the circle (detail number like 1, 2, 3)
    return (page_number, circle_text).
    """
    page_number = ""
    circle_text = ""

    page_texts = page_texts or []
    circle_texts = circle_texts or []

    # ---- Derive page_number from BOTTOM tokens ----
    if page_texts:
        joined = " ".join(page_texts)

        # 1) try flexible A9.1 pattern in the whole string
        m = re.search(r"[A-Za-z]\s*\d+\s*[\.\-]?\s*\d*", joined)
        if m:
            cand = _normalize_page_candidate(m.group(0))
            if cand:
                page_number = cand

        # 2) fallback over individual tokens
        if not page_number:
            for t in page_texts:
                cand = _normalize_page_candidate(t)
                if cand:
                    page_number = cand
                    break

        # 3) last-resort: pure decimal like 9.1 -> A9.1
        if not page_number:
            for t in page_texts:
                t_clean = t.strip()
                dec = re.fullmatch(r"\d+\.\d+", t_clean)
                if dec:
                    page_number = f"A{dec.group(0)}"
                    break

    # ---- Derive circle_text from TOP tokens ----
    for t in circle_texts:
        t_clean = t.strip()
        if re.fullmatch(r"\d{1,4}", t_clean):
            circle_text = t_clean
            break

    return page_number, circle_text



def detect_circles_with_text_from_image(img):
    """
    Core circle-detection logic that operates on an OpenCV BGR image.
    Shared by both full-image detection and region detection.
    """
    try:
        if img is None:
            print("Empty image passed to detect_circles_with_text_from_image")
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect circles using Hough Circle Transform
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=20,
            param1=50,
            param2=100,
            minRadius=50,
            maxRadius=100,
        )

        results = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")

            for i, (x, y, r) in enumerate(circles):
                # Crop region around circle with padding
                top = max(y - r - 20, 0)
                bottom = min(y + r + 20, img.shape[0])
                left = max(x - r - 20, 0)
                right = min(x + r + 20, img.shape[1])
                crop = img[top:bottom, left:right]

                # Basic preprocessing + upscaling to help OCR read small text
                try:
                    gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    gray_crop = cv2.medianBlur(gray_crop, 3)
                    crop_for_ocr = cv2.cvtColor(gray_crop, cv2.COLOR_GRAY2BGR)
                except Exception:
                    crop_for_ocr = crop

                try:
                    h_c, w_c = crop_for_ocr.shape[:2]
                    if h_c > 0 and w_c > 0:
                        scale = 3.0
                        crop_for_ocr = cv2.resize(
                            crop_for_ocr,
                            None,
                            fx=scale,
                            fy=scale,
                            interpolation=cv2.INTER_CUBIC,
                        )
                except Exception:
                    # If resize fails, fall back to original crop_for_ocr
                    pass

                top_texts: list[str] = []
                bottom_texts: list[str] = []

                try:
                    h_crop = crop_for_ocr.shape[0]
                    mid_y = h_crop / 2.0

                    if _EASYOCR_READER is not None:
                        # EasyOCR path: better for tiny, cluttered callout text
                        try:
                            crop_rgb = cv2.cvtColor(
                                crop_for_ocr, cv2.COLOR_BGR2RGB
                            )
                        except Exception:
                            crop_rgb = crop_for_ocr

                        ocr_results = _EASYOCR_READER.readtext(
                            crop_rgb, detail=1
                        )
                        for bbox, text, conf in ocr_results:
                            if not text:
                                continue
                            if conf is not None and conf < EASYOCR_MIN_CONFIDENCE:
                                continue

                            t = text.strip()
                            if not t:
                                continue

                            try:
                                ys = [pt[1] for pt in bbox]
                                center_y = sum(ys) / len(ys)
                            except Exception:
                                bottom_texts.append(t)
                                continue

                            if center_y < mid_y:
                                top_texts.append(t)
                            else:
                                bottom_texts.append(t)
                    else:
                        # Fallback: Tesseract for circle OCR (previous behavior)
                        data = _tess_image_to_data(
                            crop_for_ocr,
                            psm="6",
                            extra_config="-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-",
                        )

                        n = len(data["text"])
                        for idx in range(n):
                            t_raw = data["text"][idx] or ""
                            t = t_raw.strip()
                            if not t:
                                continue

                            conf_str = data["conf"][idx]
                            try:
                                conf = float(conf_str)
                            except (ValueError, TypeError):
                                conf = -1.0
                            if conf < 0:
                                continue

                            try:
                                top_val = int(data["top"][idx])
                                height_val = int(data["height"][idx])
                            except (ValueError, TypeError, KeyError):
                                # If geometry is missing, just treat as generic text
                                bottom_texts.append(t)
                                continue

                            center_y = top_val + height_val / 2.0
                            if center_y < mid_y:
                                top_texts.append(t)
                            else:
                                bottom_texts.append(t)
                except Exception as e:
                    print(f"OCR error for circle {i}: {e}")
                    top_texts, bottom_texts = [], []

                page_number, circle_text = _extract_page_and_circle(
                    page_texts=bottom_texts, circle_texts=top_texts
                )

                results.append(
                    {
                        "id": i + 1,
                        "x": int(x),
                        "y": int(y),
                        "r": int(r),
                        "page_number": page_number,
                        "circle_text": circle_text,
                        # Debug fields to understand what OCR saw
                        "raw_texts_top": top_texts,
                        "raw_texts_bottom": bottom_texts,
                    }
                )

        return results

    except Exception as e:
        print(f"Circle detection error: {e}")
        return []


def detect_circles_with_text_from_image_bytes(image_bytes):
    """
    Thin wrapper that decodes bytes and calls detect_circles_with_text_from_image.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            print("Failed to decode image")
            return []
        return detect_circles_with_text_from_image(img)
    except Exception as e:
        print(f"Circle detection error (bytes): {e}")
        return []


def detect_text_from_image_bytes(image_bytes):
    """
    Detects text regions from the entire image and filters them down to likely
    construction-related labels (words, room numbers, callouts).

    Steps:
    1. Convert image bytes to an OpenCV image.
    2. Run EasyOCR to detect text with bounding boxes.
    3. Skip text if it:
        - Contains quotes (single/double).
        - Contains any digits.
    4. Collect bounding box coordinates and the cleaned text.

    Returns:
        List of dictionaries containing:
        - id (int): Text index
        - x1, y1, x2, y2 (int): Bounding box coordinates
        - text (str): Extracted text string
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("Failed to decode image for text detection")
            return []

        data = _tess_image_to_data(img, psm="6")

        # Group words into line-level boxes using Tesseract's block_num + line_num
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

            # Skip text containing quotes
            if "'" in text or '"' in text:
                continue

            # Keep only construction-like tokens
            if not _is_construction_text(text):
                continue

            try:
                left = int(data["left"][i])
                top = int(data["top"][i])
                width = int(data["width"][i])
                height = int(data["height"][i])

                # Filter out very small boxes (likely noise)
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
            except Exception as e:
                print(f"Error processing text word {i}: {e}")
                continue

        # Convert grouped lines into output boxes
        text_boxes = []
        for i, (_, line) in enumerate(lines.items(), start=1):
            combined_text = " ".join(line["texts"]).strip()
            if not combined_text:
                continue

            text_boxes.append({
                "id": i,
                "x1": int(line["min_x"]),
                "y1": int(line["min_y"]),
                "x2": int(line["max_x"]),
                "y2": int(line["max_y"]),
                "text": combined_text,
            })

        return text_boxes

    except Exception as e:
        print(f"Text detection error: {e}")
        return []


@router.post("/")
async def detect_circles(file: UploadFile = File(...)):
    """
    FastAPI endpoint to detect circles and text from an uploaded image.

    Steps:
    1. Accepts an image file via POST request.
    2. Reads image bytes.
    3. Runs circle detection (with OCR inside circles).
    4. Runs general text detection across the entire image.
    5. Returns results as a JSON response containing:
        - circles: List of detected circles with text info
        - texts: List of detected text regions outside circles
    """
    try:
        image_bytes = await file.read()    
        circles_with_text = detect_circles_with_text_from_image_bytes(image_bytes)
        texts = detect_text_from_image_bytes(image_bytes)
        
        return {"circles": circles_with_text, "texts": texts}
    
    except Exception as e:
        print(f"Detection endpoint error: {e}")
        return {"error": str(e), "circles": [], "texts": []}
