"""
explainer.py

Core engine for calling LLMs to explain construction terms.
"""

import json
from typing import Optional

from construction_llm_explainer.clients import get_openai_client, get_groq_client
from construction_llm_explainer.prompts import build_system_prompt, build_user_prompt


def _parse_llm_json(raw: str) -> Optional[dict]:
    """Try to parse JSON from LLM output, handling markdown fences."""
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(raw[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return None


def explain_term(
    text: str,
    rag_context: str = "",
    drawing_context_str: str = ""
) -> dict:
    """
    Generate a structured JSON explanation from LLM.
    Tries GPT-4o first, falls back to Groq Llama-3.3-70b.
    """
    system_msg = build_system_prompt(rag_context, drawing_context_str)
    user_msg = build_user_prompt(text)

    raw = None

    # Primary: OpenAI GPT-4o
    openai_client = get_openai_client()
    if openai_client:
        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4o",
                temperature=0.2,
                max_tokens=350,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = completion.choices[0].message.content.strip()
            print("[construction_llm_explainer] Used GPT-4o (structured)")
        except Exception as e:
            print(f"[construction_llm_explainer] GPT-4o failed: {e}, falling back to Groq")

    # Fallback: Groq Llama
    groq_client = get_groq_client()
    if raw is None and groq_client:
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=350,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = completion.choices[0].message.content.strip()
            print("[construction_llm_explainer] Used Groq/Llama (structured, fallback)")
        except Exception as e:
            print(f"[construction_llm_explainer] Groq fallback also failed: {e}")

    if raw is None:
        return {
            "summary": ["No LLM backend available."],
            "key_terms": [],
            "unit_conversions": [],
            "clarifying_question": "",
            "context": rag_context,
        }

    # Parse output
    parsed = _parse_llm_json(raw)
    if parsed:
        parsed["context"] = rag_context
        # We don't merge image path here because drawing specific urls belong to web layer
        return parsed

    return {
        "summary": [raw],
        "key_terms": [],
        "unit_conversions": [],
        "clarifying_question": "",
        "context": rag_context,
    }
