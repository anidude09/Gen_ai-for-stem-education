"""
circle_ocr.py — Per-circle text extraction and page/number parsing.
"""

from __future__ import annotations

import re
import cv2
import numpy as np

from construction_ocr.engine import run_paddle_ocr
from construction_ocr.filters import clean_text


def normalize_page_candidate(raw: str) -> str | None:
    """Clean a page reference string like 'A9.1' from OCR output."""
    if not raw:
        return None
    t = raw.strip().upper()
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


def extract_page_and_circle(
    page_texts: list[str] | None, circle_texts: list[str] | None
) -> tuple[str, str]:
    """
    Given OCR tokens from a circle:
    - page_texts: from the bottom half (page number like A5.1)
    - circle_texts: from the top half (detail number like 1, 2, 3)
    """
    page_number = ""
    circle_text = ""

    page_texts = page_texts or []
    circle_texts = circle_texts or []

    if page_texts:
        joined = " ".join(page_texts)
        m = re.search(r"[A-Za-z]\s*\d+\s*[.\-]?\s*\d*", joined)
        if m:
            cand = normalize_page_candidate(m.group(0))
            if cand:
                page_number = cand
        if not page_number:
            for t in page_texts:
                cand = normalize_page_candidate(t)
                if cand:
                    page_number = cand
                    break
        if not page_number:
            for t in page_texts:
                dec = re.fullmatch(r"\d+\.\d+", t.strip())
                if dec:
                    page_number = f"A{dec.group(0)}"
                    break

    for t in circle_texts:
        t_clean = t.strip()
        if re.fullmatch(r"\d{1,4}", t_clean):
            circle_text = t_clean
            break

    return page_number, circle_text


def ocr_single_circle(
    i: int, x: int, y: int, r: int, has_hline: bool, img: np.ndarray
) -> dict:
    """
    Crop + preprocess + PaddleOCR on a single circle.

    Two circle types:
    - Detail bubble (has_hline=True):  number on top, page ref on bottom
    - Section marker (has_hline=False): just a number centered inside
    """
    # Generous padding so text near the rim isn't clipped
    pad = max(20, int(r * 0.4))
    top    = max(y - r - pad, 0)
    bottom = min(y + r + pad, img.shape[0])
    left   = max(x - r - pad, 0)
    right  = min(x + r + pad, img.shape[1])
    crop   = img[top:bottom, left:right]

    gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # Step 1 — upscale grayscale first so adaptive threshold works on more pixels
    scale = 5.0 if r < 55 else 3.0
    h_g, w_g = gray_crop.shape[:2]
    if h_g > 0 and w_g > 0:
        gray_crop = cv2.resize(gray_crop, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)

    # Step 2 — adaptive threshold on the larger image (blockSize scales with upscale)
    block = max(11, int(15 * scale) | 1)  # must be odd
    binary = cv2.adaptiveThreshold(
        gray_crop, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block, 8
    )

    # Step 3 — circular mask: blank out pixels outside the circle so external
    # text on the drawing doesn't pollute the OCR split logic
    h_b, w_b = binary.shape[:2]
    left_orig = max(x - r - pad, 0)
    top_orig  = max(y - r - pad, 0)
    cx_s = int((x - left_orig) * scale)
    cy_s = int((y - top_orig)  * scale)
    r_s  = int(r * scale)
    mask = np.zeros((h_b, w_b), dtype=np.uint8)
    cv2.circle(mask, (cx_s, cy_s), r_s + int(pad * scale * 0.5), 255, -1)
    binary = cv2.bitwise_and(binary, binary, mask=mask)
    # Restore white background outside mask so OCR sees clean margins
    binary[mask == 0] = 255

    crop_for_ocr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    top_texts: list[str] = []
    bottom_texts: list[str] = []
    all_texts: list[str] = []

    try:
        h_crop = crop_for_ocr.shape[0]
        mid_y = h_crop / 2.0
        ocr_results = run_paddle_ocr(crop_for_ocr)

        for pts, text, conf in ocr_results:
            t = clean_text(text)
            if not t:
                continue
            all_texts.append(t)
            if has_hline:
                try:
                    ys = [p[1] for p in pts]
                    center_y = sum(ys) / len(ys)
                except Exception:
                    bottom_texts.append(t)
                    continue
                if center_y < mid_y:
                    top_texts.append(t)
                else:
                    bottom_texts.append(t)
    except Exception as e:
        print(f"[circle_detector] Circle {i} OCR error: {e}")

    if has_hline:
        page_number, circle_text = extract_page_and_circle(
            page_texts=bottom_texts, circle_texts=top_texts
        )
    else:
        page_number = ""
        circle_text = ""
        for t in all_texts:
            num_match = re.search(r'\d{1,4}', t)
            if num_match:
                circle_text = num_match.group(0)
                break

    ctype = "detail" if has_hline else "marker"
    print(f"[circle_detector] Circle {i+1} @ ({x},{y}) r={r} [{ctype}]: "
          f"texts={all_texts}, circle_text='{circle_text}', page='{page_number}'")

    return {
        "id": i + 1,
        "x": int(x),
        "y": int(y),
        "r": int(r),
        "page_number": page_number,
        "circle_text": circle_text,
        "raw_texts_top": top_texts,
        "raw_texts_bottom": bottom_texts,
    }
