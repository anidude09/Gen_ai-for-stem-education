"""
preprocess.py — Image preprocessing utilities for construction drawings.
"""

from __future__ import annotations

import cv2
import numpy as np

# Shared CLAHE instance
_CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def preprocess_for_ocr(img_bgr: np.ndarray) -> np.ndarray:
    """CLAHE contrast enhancement for construction drawings."""
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        enhanced = _CLAHE.apply(gray)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    except Exception:
        return img_bgr


def preprocess_gray(img_bgr: np.ndarray) -> np.ndarray:
    """Grayscale + CLAHE + Gaussian blur for circle detection."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    enhanced = _CLAHE.apply(gray)
    return cv2.GaussianBlur(enhanced, (5, 5), 1.5)
