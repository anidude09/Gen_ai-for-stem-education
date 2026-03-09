"""
pipeline.py — Full circle detection pipeline.

Combines raw detection + filtering + per-circle OCR into a single
high-level function: detect_circles(img).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np

from construction_ocr.preprocess import preprocess_gray
from construction_circle_detector.detect import detect_circles_raw
from construction_circle_detector.validate import filter_circles
from construction_circle_detector.circle_ocr import ocr_single_circle

# Thread pool for concurrent per-circle OCR
_OCR_POOL = ThreadPoolExecutor(max_workers=4)


def detect_circles(img: np.ndarray) -> list[dict]:
    """
    Detect detail-bubble circles and OCR their contents.

    Args:
        img: BGR image as numpy array.

    Returns:
        List of dicts: [{id, x, y, r, page_number, circle_text, ...}, ...]
    """
    try:
        if img is None:
            return []

        gray = preprocess_gray(img)
        raw_circles = detect_circles_raw(gray)
        circles = filter_circles(raw_circles, gray)

        if not circles:
            return []

        # Submit all circle OCR tasks concurrently
        futures = {
            _OCR_POOL.submit(ocr_single_circle, i, x, y, r, hl, img): i
            for i, (x, y, r, hl) in enumerate(circles)
        }

        results_map: dict[int, dict] = {}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                results_map[idx] = fut.result()
            except Exception as e:
                print(f"[circle_detector] Circle {idx} OCR future failed: {e}")

        return [results_map[i] for i in sorted(results_map)]

    except Exception as e:
        print(f"[circle_detector] Circle detection error: {e}")
        return []


def detect_circles_from_bytes(image_bytes: bytes) -> list[dict]:
    """Convenience: decode bytes → detect circles."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return []
        return detect_circles(img)
    except Exception as e:
        print(f"[circle_detector] Circle detection error (bytes): {e}")
        return []
