"""
prompts.py

Utility for building a human-readable drawing context string from VLM output.
Prompts themselves are defined centrally in backend/prompts.py and passed to explain_term().
"""

from typing import Optional, Dict, Any


def build_drawing_context_str(drawing_context: Optional[Dict[str, Any]]) -> str:
    """Build a human-readable context string from VLM analysis results."""
    if not drawing_context:
        return ""

    parts = []
    if drawing_context.get("drawing_type"):
        parts.append(f"Drawing Type: {drawing_context['drawing_type']}")
    if drawing_context.get("summary"):
        summaries = drawing_context["summary"]
        if isinstance(summaries, list):
            parts.append("Drawing Summary: " + "; ".join(summaries))
        else:
            parts.append(f"Drawing Summary: {summaries}")
    if drawing_context.get("text_labels"):
        labels = drawing_context["text_labels"]
        label_strs = []
        for lbl in labels[:10]:
            text = lbl.get("text", "")
            cat = lbl.get("category", "")
            if text:
                label_strs.append(f"{text} ({cat})" if cat else text)
        if label_strs:
            parts.append("Detected Labels: " + ", ".join(label_strs))

    if not parts:
        return ""
    return "\n--- Drawing Context (from VLM analysis) ---\n" + "\n".join(parts)
