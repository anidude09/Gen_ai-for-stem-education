"""
detect.py — Raw circle detection using Hough transform and contour analysis.
"""

from __future__ import annotations

import cv2
import numpy as np

# ── Circle detection config ───────────────────────────────────────────────
HOUGH_SCALES = [
    (43, 47),   # small detail bubbles
    (63, 75),   # large detail bubbles
]
HOUGH_DP        = 1.2
HOUGH_MIN_DIST  = 50
HOUGH_PARAM1    = 80
HOUGH_PARAM2    = 55

CONTOUR_CIRCULARITY = 0.80
CONTOUR_MIN_RADIUS  = 35
CONTOUR_MAX_RADIUS  = 90

CIRCLE_NMS_IOU = 0.30


def circle_iou(c1, c2):
    """IoU for two circles represented as (x, y, radius)."""
    x1, y1, r1 = c1
    x2, y2, r2 = c2
    ax1, ay1, ax2, ay2 = x1 - r1, y1 - r1, x1 + r1, y1 + r1
    bx1, by1, bx2, by2 = x2 - r2, y2 - r2, x2 + r2, y2 + r2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def nms_circles(circles):
    """Non-maximum suppression for circles."""
    if not circles:
        return circles
    dets = sorted(circles, key=lambda c: c[2], reverse=True)
    keep = []
    for det in dets:
        if not any(circle_iou(det, k) > CIRCLE_NMS_IOU for k in keep):
            keep.append(det)
    return keep


def detect_circles_raw(gray):
    """Multi-scale Hough + contour-based detection → raw circle list."""
    all_circles = []

    # Method 1: HoughCircles
    for min_r, max_r in HOUGH_SCALES:
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT,
            dp=HOUGH_DP, minDist=HOUGH_MIN_DIST,
            param1=HOUGH_PARAM1, param2=HOUGH_PARAM2,
            minRadius=min_r, maxRadius=max_r,
        )
        if circles is not None:
            for c in np.round(circles[0, :]).astype(int):
                all_circles.append((int(c[0]), int(c[1]), int(c[2])))

    # Method 2: Contour-based
    edges_raw = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    edges_d = cv2.dilate(edges_raw, kernel, iterations=1)
    contours, _ = cv2.findContours(edges_d, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        perimeter = cv2.arcLength(cnt, True)
        area = cv2.contourArea(cnt)
        if perimeter == 0 or area < 800:
            continue
        circ = (4 * np.pi * area) / (perimeter ** 2)
        if circ < CONTOUR_CIRCULARITY:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        radius, cx, cy = int(radius), int(cx), int(cy)
        if radius < CONTOUR_MIN_RADIUS or radius > CONTOUR_MAX_RADIUS:
            continue
        expected = np.pi * radius * radius
        if area / expected < 0.65:
            continue
        all_circles.append((cx, cy, radius))

    return all_circles
