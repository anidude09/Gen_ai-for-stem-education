"""
construction_ocr — PaddleOCR wrapper optimized for construction drawings.

Public API:
    detect_text(img)          → list of {id, x1, y1, x2, y2, text}
    is_construction_text(t)   → bool
    clean_text(t)             → str
"""

from construction_ocr.pipeline import detect_text
from construction_ocr.filters import is_construction_text, clean_text
from construction_ocr.engine import get_paddle_ocr, run_paddle_ocr, run_paddle_ocr_tiled

__all__ = [
    "detect_text",
    "is_construction_text",
    "clean_text",
    "get_paddle_ocr",
    "run_paddle_ocr",
    "run_paddle_ocr_tiled",
]
