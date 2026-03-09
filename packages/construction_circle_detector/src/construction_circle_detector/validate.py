"""
validate.py — Circle validation (edge + horizontal line detection).
"""

from __future__ import annotations

import cv2
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────
EDGE_SAMPLE_POINTS     = 36
EDGE_MIN_RATIO         = 0.55
HLINE_MIN_WIDTH_RATIO  = 0.40


def validate_circle_edges(edges, cx, cy, r):
    """Check if edge pixels exist along the circumference."""
    h, w = edges.shape[:2]
    hits = 0
    tolerance = max(3, int(r * 0.07))
    for i in range(EDGE_SAMPLE_POINTS):
        angle = 2 * np.pi * i / EDGE_SAMPLE_POINTS
        px = int(cx + r * np.cos(angle))
        py = int(cy + r * np.sin(angle))
        x1, x2 = max(0, px - tolerance), min(w, px + tolerance + 1)
        y1, y2 = max(0, py - tolerance), min(h, py + tolerance + 1)
        if x2 <= x1 or y2 <= y1:
            continue
        if np.any(edges[y1:y2, x1:x2] > 0):
            hits += 1
    return hits / EDGE_SAMPLE_POINTS if EDGE_SAMPLE_POINTS > 0 else 0


def has_horizontal_line(gray, cx, cy, r):
    """Check for horizontal dividing line — signature of a detail bubble."""
    h, w = gray.shape[:2]
    band_half = max(3, int(r * 0.20))
    y_start = max(0, cy - band_half)
    y_end   = min(h, cy + band_half + 1)
    x_start = max(0, cx - r + 5)
    x_end   = min(w, cx + r - 5)
    if x_end <= x_start or y_end <= y_start:
        return False

    crop = gray[y_start:y_end, x_start:x_end]
    _, binary = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    min_line = int((x_end - x_start) * HLINE_MIN_WIDTH_RATIO)

    for row_idx in range(binary.shape[0]):
        max_run = current = 0
        for pixel in binary[row_idx, :]:
            if pixel > 0:
                current += 1
                max_run = max(max_run, current)
            else:
                current = 0
        if max_run >= min_line:
            return True
    return False


def filter_circles(raw_circles, gray):
    """NMS → edge validation → horizontal line tagging."""
    from construction_circle_detector.detect import nms_circles

    after_nms = nms_circles(raw_circles)

    edges = cv2.Canny(gray, 50, 150)
    after_edges = [
        c for c in after_nms
        if validate_circle_edges(edges, *c) >= EDGE_MIN_RATIO
    ]

    final = []
    for c in after_edges:
        hline = has_horizontal_line(gray, *c)
        final.append((c[0], c[1], c[2], hline))

    return final
