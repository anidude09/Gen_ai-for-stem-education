"""
construction_vlm_analyzer — GPT-4o Vision analysis for construction drawings.

Public API:
    analyze_drawing(img_pil, crop_region=None)  → structured JSON dict
"""

from construction_vlm_analyzer.analyzer import analyze_drawing

__all__ = ["analyze_drawing"]
