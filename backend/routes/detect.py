"""
detect.py

OCR: EasyOCR only (GPU preferred, CPU fallback), with:
- Blueprint cleanup (remove grid/line noise)
- Tuned EasyOCR params for small/dense text
- Optional tiling for large images to preserve small text

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

# EasyOCR is the sole OCR engine (GPU preferred, CPU fallback).
try:
    import easyocr  # type: ignore

    try:
        _EASYOCR_READER = easyocr.Reader(["en"], gpu=True)
    except Exception:
        _EASYOCR_READER = easyocr.Reader(["en"], gpu=False)
except Exception:
    _EASYOCR_READER = None

# Detection tuning parameters (can be adjusted if needed)
MIN_BOX_WIDTH = 10     # ignore very tiny boxes (pixels)
MIN_BOX_HEIGHT = 10
EASYOCR_MIN_CONFIDENCE = 0.3  # EasyOCR confidence threshold

# EasyOCR tuning for blueprints - Simplified for robustness
EASYOCR_PARAMS = {
    "paragraph": False,
    "text_threshold": 0.5,  # Lower threshold to detect faint text
    "low_text": 0.35,       # Keep lower confidence text regions
    "link_threshold": 0.4,  # Default merging behavior
    "mag_ratio": 1.5,       # Magnify image to detect small text
}

# Tiling parameters (unused in simplified mode)
TILE_SIZE = 1000
TILE_OVERLAP = 0.20
TILE_RESIZE = 600
TILE_BORDER = 10
TILE_SKIP_MEAN = 245

# Initialize FastAPI router for detection-related endpoints
router = APIRouter()


def _preprocess_for_easyocr(img_bgr: np.ndarray) -> np.ndarray:
    """
    Light preprocessing to help EasyOCR on construction drawings:
    - Convert to grayscale
    - Apply CLAHE for local contrast enhancement
    - Convert back to 3-channel BGR (EasyOCR expects 3-channel images)
    """
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    except Exception:
        return img_bgr


def _remove_blueprint_lines(img_bgr: np.ndarray) -> np.ndarray:
    """
    Remove long horizontal/vertical lines (grid/walls) to reduce OCR noise.
    """
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Remove horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        remove_horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        cnts = cv2.findContours(remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(gray, [c], -1, (255, 255, 255), 5)

        # Remove vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        remove_vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        cnts = cv2.findContours(remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(gray, [c], -1, (255, 255, 255), 5)

        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    except Exception:
        return img_bgr


def _tile_image(img: np.ndarray, tile_size: int = TILE_SIZE, overlap: float = TILE_OVERLAP):
    """Yield tiles with their top-left offsets."""
    h, w = img.shape[:2]
    step = int(tile_size * (1 - overlap))
    for y in range(0, max(h - tile_size, 0) + 1, max(step, 1)):
        for x in range(0, max(w - tile_size, 0) + 1, max(step, 1)):
            tile = img[y:y + tile_size, x:x + tile_size]
            yield x, y, tile


def _run_easyocr(img_bgr: np.ndarray, params: dict):
    """Run EasyOCR with given params and return raw results."""
    if _EASYOCR_READER is None:
        print("EasyOCR reader not initialized; cannot perform text detection")
        return []
    try:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        img_rgb = img_bgr
    return _EASYOCR_READER.readtext(img_rgb, detail=1, **params)


def _unpack_easyocr_line(line):
    """
    Normalize EasyOCR output to (bbox, text, conf), handling 2- or 3-tuples.
    Returns (None, None, None) if the line is malformed.
    """
    try:
        if len(line) == 3:
            return line[0], line[1], line[2]
        if len(line) == 2:
            return line[0], line[1], None
    except Exception:
        pass
    return None, None, None


def _clean_text(t: str) -> str:
    """
    Normalize OCR text:
    - Uppercase
    - Collapse multiple spaces
    - Strip quotes
    - Drop trailing slash/dash/period if it's dangling
    """
    t = t.strip().upper()
    t = re.sub(r"\s+", " ", t)
    t = t.strip(" '\"")
    if re.match(r".+[\\/.\-]$", t) and not re.search(r"[A-Z0-9][\\/.\-][A-Z0-9]$", t):
        t = t[:-1]
    return t.strip()


def _is_construction_text(text: str) -> bool:
    """
    Heuristic to keep likely construction/plan labels and drop obvious noise.
    """
    if not text:
        return False

    t = text.strip()
    if len(t) < 2:
        return False

    # Allow spaces and common construction chars (dash at end to avoid range issues)
    if not re.match(r"^[A-Za-z0-9.\"'\/()\s-]+$", t):
        return False

    # Token-level patterns
    patterns = [
        r"^[A-Z]{3,}$",                # WORDS like CORRIDOR
        r"^(UP|DN|NO|ID|LV|EL|TYP|RM)$", # Common 2-letter abbrs
        r"^[A-Z]+\d+[A-Z]?$",          # W1, W12A
        r"^[A-Z]+\d+(\.\d+)?$",        # A3.1, B12.2
        r"^\d{2,4}$",                  # 101, 1203
        r"^\d+(\.\d+)?[\"']?$",        # 12", 12.5, 12.5"
        r"^\d+\/\d+[\"']?$",           # 1/2", 3/4"
    ]

    tokens = t.split()
    hit = False
    for tok in tokens:
        tok = tok.strip()
        # Allow short tokens if they match the 2-letter pattern, otherwise len>=2
        if len(tok) < 2:
            continue
            
        for pat in patterns:
            if re.match(pat, tok):
                hit = True
                break
        if hit:
            break
    # If any token matches a constructiony pattern, keep it
    if hit:
        return True

    # Otherwise, allow if all tokens are alpha words length>=3
    if all(len(tok) >= 3 and tok.isalpha() for tok in tokens):
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
                crop_for_ocr = _preprocess_for_easyocr(crop)
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
                        try:
                            crop_rgb = cv2.cvtColor(crop_for_ocr, cv2.COLOR_BGR2RGB)
                        except Exception:
                            crop_rgb = crop_for_ocr

                        ocr_results = _run_easyocr(crop_rgb, EASYOCR_PARAMS)
                        for line in ocr_results:
                            bbox, text, conf = _unpack_easyocr_line(line)
                            if not text or bbox is None:
                                continue
                            if conf is not None and conf < EASYOCR_MIN_CONFIDENCE:
                                continue

                            t = _clean_text(text)
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
                        print("EasyOCR reader not initialized; skipping circle OCR")
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
    Detects text regions from the entire image using EasyOCR and filters them
    down to plausible labels.

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

        if _EASYOCR_READER is None:
            print("EasyOCR reader not initialized; cannot perform text detection")
            return []

        text_boxes: list[dict] = []
        idx = 1

        def process_results(ocr_results, x_offset=0, y_offset=0, apply_filter=True):
            nonlocal idx
            for line in ocr_results:
                bbox, text, conf = _unpack_easyocr_line(line)
                if not text or bbox is None:
                    continue
                if conf is not None and conf < EASYOCR_MIN_CONFIDENCE:
                    continue

                t = _clean_text(text)
                if len(t) < 2:
                    continue

                if apply_filter and not _is_construction_text(t):
                    continue

                try:
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
                            "x1": int(min_x + x_offset),
                            "y1": int(min_y + y_offset),
                            "x2": int(max_x + x_offset),
                            "y2": int(max_y + y_offset),
                            "text": t,
                        }
                    )
                    idx += 1
                except Exception as e:
                    print(f"Error processing EasyOCR text box: {e}")
                    continue

        # Pass 1: Preprocessed image (CLAHE)
        img_proc = _preprocess_for_easyocr(img)
        ocr_results_1 = _run_easyocr(img_proc, EASYOCR_PARAMS)
        if ocr_results_1:
            process_results(ocr_results_1, x_offset=0, y_offset=0, apply_filter=True)

        # Pass 2: Raw image (if Pass 1 results are sparse, or to catch missed text)
        # We run this if we found fewer than 5 items, OR always run it to be safe?
        # Given "no text detected" complaints, let's be aggressive and run it if < 10 items.
        if len(text_boxes) < 10:
            ocr_results_2 = _run_easyocr(img, EASYOCR_PARAMS)
            if ocr_results_2:
                process_results(ocr_results_2, x_offset=0, y_offset=0, apply_filter=True)

        # Deduplicate based on overlap and text content
        unique_boxes = []
        for box in text_boxes:
            is_dup = False
            for exist in unique_boxes:
                # Check roughly if same text and same location
                if box["text"] == exist["text"]:
                    # Center distance
                    cx1 = (box["x1"] + box["x2"]) / 2
                    cy1 = (box["y1"] + box["y2"]) / 2
                    cx2 = (exist["x1"] + exist["x2"]) / 2
                    cy2 = (exist["y1"] + exist["y2"]) / 2
                    dist = ((cx1 - cx2)**2 + (cy1 - cy2)**2)**0.5
                    if dist < 50:  # 50 pixels tolerance
                        is_dup = True
                        break
            if not is_dup:
                unique_boxes.append(box)

        # ---------------------------------------------------------
        # Group vertical text blocks (e.g. "OPEN SHELL" above "107")
        # ---------------------------------------------------------
        # We repeat the merge pass until no more merges happen (handling 3+ lines)
        while True:
            # Sort by Y primarily to find top-down pairs
            unique_boxes.sort(key=lambda b: (b["y1"], b["x1"]))
            
            merged_boxes = []
            used_indices = set()
            has_merge = False

            for i in range(len(unique_boxes)):
                if i in used_indices:
                    continue
                
                base = unique_boxes[i]
                merged_this_iter = False
                
                # Look for immediate neighbor below
                for j in range(i + 1, len(unique_boxes)):
                    if j in used_indices:
                        continue
                    
                    cand = unique_boxes[j]
                    
                    # Vertical gap check
                    # cand should be below base
                    v_gap = cand["y1"] - base["y2"]
                    base_h = base["y2"] - base["y1"]
                    
                    # If gap is too huge, stop looking? 
                    # Not necessarily, as there might be other boxes in different columns.
                    # But for performance, we can limit search scope if needed.
                    # For now, just check criteria.
                    
                    # Criteria 1: Vertical proximity
                    # Allow small gap (e.g. < height of top box) or slight overlap
                    if -5 <= v_gap <= base_h * 1.2:
                        # Criteria 2: Horizontal alignment
                        b_x1, b_x2 = base["x1"], base["x2"]
                        c_x1, c_x2 = cand["x1"], cand["x2"]
                        
                        overlap_start = max(b_x1, c_x1)
                        overlap_end = min(b_x2, c_x2)
                        overlap_len = overlap_end - overlap_start
                        
                        min_width = min(b_x2 - b_x1, c_x2 - c_x1)
                        
                        # Significant overlap (> 30% of smaller width)
                        if overlap_len > 0 and (overlap_len / min_width) > 0.3:
                            # Merge
                            new_box = {
                                "id": base["id"],
                                "x1": min(b_x1, c_x1),
                                "y1": min(base["y1"], cand["y1"]),
                                "x2": max(b_x2, c_x2),
                                "y2": max(base["y2"], cand["y2"]),
                                "text": base["text"] + " " + cand["text"]
                            }
                            merged_boxes.append(new_box)
                            used_indices.add(i)
                            used_indices.add(j)
                            merged_this_iter = True
                            has_merge = True
                            break 
                
                if not merged_this_iter:
                    merged_boxes.append(base)
                    used_indices.add(i)
            
            if not has_merge:
                break
            unique_boxes = merged_boxes

        # Re-index
        for i, box in enumerate(unique_boxes):
            box["id"] = i + 1

        return unique_boxes

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
