"""
construction_llm_explainer — Explains construction terminology using GPT-4o and Groq Llama fallback.

Public API:
    explain_term(text, rag_context, drawing_context_str) -> dict
"""

from construction_llm_explainer.explainer import explain_term
from construction_llm_explainer.prompts import build_drawing_context_str

__all__ = ["explain_term", "build_drawing_context_str"]
