"""
construction_circle_detector — Circle detection for construction drawings.

Public API:
    detect_circles(img)  → list of circle dicts with text + page references
"""

from construction_circle_detector.pipeline import detect_circles, detect_circles_from_bytes

__all__ = [
    "detect_circles",
    "detect_circles_from_bytes",
]
