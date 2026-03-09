"""
pipeline.py — Full text detection pipeline for construction drawings.

Combines OCR engine + filters + dedup + vertical merge into a single
high-level function: detect_text(img).
"""

from __future__ import annotations

import numpy as np
import cv2

from construction_ocr.engine import get_paddle_ocr, run_paddle_ocr_tiled
from construction_ocr.filters import clean_text, is_construction_text

# ── Configuration ─────────────────────────────────────────────────────────
MIN_BOX_WIDTH  = 10
MIN_BOX_HEIGHT = 10


# ── Deduplication ─────────────────────────────────────────────────────────

def _dedup_boxes(text_boxes: list[dict]) -> list[dict]:
    """Remove near-duplicate text boxes (same text within 50px)."""
    if not text_boxes:
        return []
    text_boxes_sorted = sorted(text_boxes, key=lambda b: b["text"])
    unique: list[dict] = []
    for box in text_boxes_sorted:
        cx = (box["x1"] + box["x2"]) / 2
        cy = (box["y1"] + box["y2"]) / 2
        dup = False
        for exist in reversed(unique):
            if exist["text"] != box["text"]:
                break
            ecx = (exist["x1"] + exist["x2"]) / 2
            ecy = (exist["y1"] + exist["y2"]) / 2
            if ((cx - ecx) ** 2 + (cy - ecy) ** 2) ** 0.5 < 50:
                dup = True
                break
        if not dup:
            unique.append(box)
    return unique


def _merge_vertical(boxes: list[dict]) -> list[dict]:
    """Merge vertically stacked text blocks into single boxes."""
    unique_boxes = list(boxes)
    while True:
        unique_boxes.sort(key=lambda b: (b["y1"], b["x1"]))
        merged_boxes = []
        used: set[int] = set()
        has_merge = False

        for i in range(len(unique_boxes)):
            if i in used:
                continue
            base = unique_boxes[i]
            merged = False
            for j in range(i + 1, len(unique_boxes)):
                if j in used:
                    continue
                cand = unique_boxes[j]
                v_gap  = cand["y1"] - base["y2"]
                base_h = base["y2"] - base["y1"]
                if -5 <= v_gap <= base_h * 1.2:
                    b_x1, b_x2 = base["x1"], base["x2"]
                    c_x1, c_x2 = cand["x1"], cand["x2"]
                    overlap_len = min(b_x2, c_x2) - max(b_x1, c_x1)
                    min_w = min(b_x2 - b_x1, c_x2 - c_x1)
                    if overlap_len > 0 and (overlap_len / min_w) > 0.3:
                        merged_boxes.append({
                            "id": base["id"],
                            "x1": min(b_x1, c_x1),
                            "y1": min(base["y1"], cand["y1"]),
                            "x2": max(b_x2, c_x2),
                            "y2": max(base["y2"], cand["y2"]),
                            "text": base["text"] + " " + cand["text"],
                        })
                        used.add(i)
                        used.add(j)
                        merged = True
                        has_merge = True
                        break
            if not merged:
                merged_boxes.append(base)
                used.add(i)

        if not has_merge:
            break
        unique_boxes = merged_boxes

    for i, box in enumerate(unique_boxes):
        box["id"] = i + 1

    return unique_boxes


# ── Public API ────────────────────────────────────────────────────────────

def detect_text(img: np.ndarray) -> list[dict]:
    """
    Detect text regions in a construction drawing using PaddleOCR.

    Args:
        img: BGR image as numpy array.

    Returns:
        List of dicts: [{id, x1, y1, x2, y2, text}, ...]
    """
    if img is None:
        return []
    if get_paddle_ocr() is None:
        print("[construction_ocr] PaddleOCR not available for text detection")
        return []

    ocr_results = run_paddle_ocr_tiled(img)

    text_boxes: list[dict] = []
    idx = 1

    for pts, text, conf in ocr_results:
        t = clean_text(text)
        if len(t) < 2:
            continue
        if not is_construction_text(t):
            continue
        try:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            width  = max_x - min_x
            height = max_y - min_y
            if width < MIN_BOX_WIDTH or height < MIN_BOX_HEIGHT:
                continue
            text_boxes.append({
                "id": idx,
                "x1": int(min_x),
                "y1": int(min_y),
                "x2": int(max_x),
                "y2": int(max_y),
                "text": t,
            })
            idx += 1
        except Exception as e:
            print(f"[construction_ocr] Text box error: {e}")

    unique_boxes = _dedup_boxes(text_boxes)
    return _merge_vertical(unique_boxes)


def detect_text_from_bytes(image_bytes: bytes) -> list[dict]:
    """Convenience: decode bytes → detect text."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return detect_text(img)
    except Exception as e:
        print(f"[construction_ocr] Text detection error: {e}")
        return []
