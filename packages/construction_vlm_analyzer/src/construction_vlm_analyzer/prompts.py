"""
prompts.py — Response parsing logic for VLM output.

Prompts are defined centrally in backend/prompts.py and passed to analyze_drawing().
"""

from __future__ import annotations

import json


def parse_vlm_response(raw: str) -> dict:
    """Parse the VLM JSON response, with fallback on malformed output."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from surrounding noise
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
    # Final fallback — wrap raw text so the frontend always gets a valid structure
    return {
        "drawing_type": "Unknown",
        "summary": [raw[:500]] if raw else ["No response received."],
        "text_labels": [],
        "detail_circles": [],
        "symbols": [],
        "student_tip": "",
    }
