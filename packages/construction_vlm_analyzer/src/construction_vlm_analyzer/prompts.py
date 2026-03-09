"""
prompts.py — System prompt and response parsing logic.
"""

from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "You are an expert construction engineer acting as a professor for freshman "
    "Construction Management students who have no prior background. "
    "Analyze the provided construction drawing or drawing region and explain it "
    "clearly, using plain English. Always reference what you can actually see in "
    "the image — do not invent details.\n\n"
    "Return ONLY a valid JSON object with these exact keys:\n"
    "- drawing_type: string — the type of drawing (e.g. 'Floor Plan', 'Section', "
    "  'Detail', 'Elevation', 'Site Plan', 'Region of a Floor Plan')\n"
    "- summary: array of 2-4 plain-language bullet strings describing what this "
    "  drawing/region shows and its purpose on a construction project\n"
    "- text_labels: array of {text, category, explanation} objects for the most "
    "  important labels visible. category must be one of: room_name, dimension, "
    "  annotation, abbreviation, symbol, reference, material, other\n"
    "- detail_circles: array of {number, page_reference, meaning} for any detail "
    "  bubble/callout circles visible (e.g. number='3', page_reference='A9.1')\n"
    "- symbols: array of {type, description} for non-text graphic symbols visible\n"
    "- student_tip: one practical sentence a student should keep in mind when "
    "  reading this type of drawing on a real construction site\n\n"
    "Output ONLY the JSON object. No markdown fences, no extra text."
)


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
