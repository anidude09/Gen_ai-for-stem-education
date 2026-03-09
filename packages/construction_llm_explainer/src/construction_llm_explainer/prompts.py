"""
prompts.py

System and user prompts for the LLM explainer.
Includes helper to build the human-readable drawing context from VLM output.
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
        for lbl in labels[:10]:  # limit to 10 labels
            text = lbl.get("text", "")
            cat = lbl.get("category", "")
            if text:
                label_strs.append(f"{text} ({cat})" if cat else text)
        if label_strs:
            parts.append("Detected Labels: " + ", ".join(label_strs))

    if not parts:
        return ""
    return "\n--- Drawing Context (from VLM analysis) ---\n" + "\n".join(parts)


def build_system_prompt(rag_context: str, drawing_context_str: str) -> str:
    """Build the shared system prompt for both GPT and Groq."""
    return (
        "You are an instructor of a Construction Plan Reading course. "
        "You need to help undergraduate freshman students in the Construction "
        "Management program, who have no prior construction background, "
        "understand construction plans by providing clear and easy-to-understand explanations.\n\n"
        "Instructions:\n"
        "1. Use only the detected text or symbols, and interpret them within "
        "the context of a Construction Project.\n"
        "2. You may include general conventions typical in construction "
        "documents when the snippet consists only of a short label or title.\n"
        "3. Respond ONLY with a valid JSON object that matches the requested schema.\n"
        "4. Do not include any preface, explanation, or code fences.\n"
        "5. All explanations must be provided strictly from the Building/Housing "
        "Construction perspective.\n"
        "6. Use the provided 'Context from Dictionary' (if any) to act as an authoritative source.\n"
        "7. If 'Drawing Context' is provided, use it to give more specific, "
        "contextual explanations about what the text means in this particular drawing.\n\n"
        "Schema (JSON keys):\n"
        '- summary: 2-3 bullets (plain language, 60-120 words total)\n'
        '- key_terms: array of {"term": str, "definition": str} only if defined in snippet\n'
        '- unit_conversions: array of {"original": str, "si": str} where applicable\n'
        "- clarifying_question: one question if context is insufficient, else empty string\n\n"
        "Constraints:\n"
        '- Expand acronyms only if defined in the snippet; else note "not defined here".\n'
        '- If not construction-related, set summary to ["Out of scope for construction"] '
        "and provide a clarifying_question.\n"
        '- If the snippet is very short (e.g., a sheet title such as "FIRST FLOOR PLAN"), '
        "treat it as a drawing/section label and explain its typical role in "
        "construction documents without assumptions specific to a particular "
        "construction project.\n"
        "- Output ONLY the JSON object. No additional text.\n\n"
        f"Context from Dictionary:\n{rag_context}"
        f"{drawing_context_str}"
    )


def build_user_prompt(text: str) -> str:
    """Build the shared user prompt."""
    return (
        "Detected construction-plan text or symbol:\n"
        "```SNIPPET\n"
        f"{text}\n"
        "```\n\n"
        "Using the above snippet, generate the JSON object according to the "
        "schema and constraints in the system instructions."
    )
