"""
llm.py

This module defines a FastAPI router for interacting with a Large Language Model (LLM) 
using the Groq API. 

Key functionalities:
- Accept user-provided text.
- Query an LLM (LLaMA-3.1-8b-instant) via Groq.
- Return a simplified explanation of the input text in less than 100 words.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import Groq
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Initialize Groq client with API key
client = Groq(api_key=api_key)

# Initialize FastAPI router for LLM endpoints
router = APIRouter()


class LLMRequest(BaseModel):
    """
    Request model for generating simplified information from text.

    Fields:
        - content (str): The raw text content provided by the user.
    """
    content: str


def generate_info_from_llm(text: str) -> str:
    """
    Sends the given text to the Groq LLM (LLaMA-3.1-8b-instant) and requests a
    concise, domain-aware explanation (construction) with light guardrails.

    Steps:
    1. Create a chat completion request with the model.
    2. Provide a system persona and explicit rules to improve accuracy.
    3. Prompt the LLM to explain the input text in 2–4 concise bullets (60–120 words).
    3. Extract and return the model's response as a string.

    Args:
        text (str): The text to be explained.

    Returns:
        str: Concise explanation of the input text.
    """
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        max_tokens=220,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior construction engineer and technical editor. "
                    "Explain snippets from construction management/engineering research papers for an undergraduate civil engineering audience.\n"
                    "Rules:\n"
                    "1) Use only the provided text; do not invent facts.\n"
                    "2) Preserve quantities/units; if units are imperial, also give SI in parentheses.\n"
                    "3) Expand acronyms only if defined in the snippet; otherwise say 'not defined here'.\n"
                    "4) If there is an equation, state what it calculates and define each variable present in the snippet.\n"
                    "5) If the snippet is a figure/table caption, explain what it shows and the practical implication.\n"
                    "6) If content is not about construction or lacks enough context, say so briefly and ask 1 clarifying question.\n"
                    "7) Output 2–4 concise bullet points, total 60–120 words."
                )
            },
            {
                "role": "user",
                "content": f"Snippet:\n{text}"
            }
        ],
    )
    return completion.choices[0].message.content.strip()


@router.post("/generate_info")
async def generate_info_endpoint(request: LLMRequest):
    """
    FastAPI endpoint to generate simplified information from user text.

    Steps:
    1. Accept a POST request with JSON containing `content`.
    2. Pass the content to the `generate_info_from_llm` function.
    3. Return the simplified explanation in JSON format.
    """
    try:
        info = generate_info_from_llm(request.content)
        return {"info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_info_from_llm_structured(text: str) -> dict:
    """
    Variant that requests a strict JSON response to support structured rendering.

    Returns a dict with keys:
      - summary: list[str]
      - key_terms: list[{"term": str, "definition": str}]
      - unit_conversions: list[{"original": str, "si": str}]
      - clarifying_question: str
    """
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        max_tokens=350,
        messages=[
            {
                "role": "system",
                "content": (
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
                    "Construction perspective.\n\n"
                    "Schema (JSON keys):\n"
                    '- summary: 2–3 bullets (plain language, 60–120 words total)\n'
                    '- key_terms: array of {\"term\": str, \"definition\": str} only if defined in snippet\n'
                    '- unit_conversions: array of {\"original\": str, \"si\": str} where applicable\n'
                    "- clarifying_question: one question if context is insufficient, else empty string\n\n"
                    "Constraints:\n"
                    '- Expand acronyms only if defined in the snippet; else note "not defined here".\n'
                    '- If not construction-related, set summary to ["Out of scope for construction"] '
                    "and provide a clarifying_question.\n"
                    '- If the snippet is very short (e.g., a sheet title such as "FIRST FLOOR PLAN"), '
                    "treat it as a drawing/section label and explain its typical role in "
                    "construction documents without assumptions specific to a particular "
                    "construction project.\n"
                    "- Output ONLY the JSON object. No additional text."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Detected construction-plan text or symbol:\n"
                    "```SNIPPET\n"
                    f"{text}\n"
                    "```\n\n"
                    "Using the above snippet, generate the JSON object according to the "
                    "schema and constraints in the system instructions."
                ),
            },
        ],
    )

    raw = completion.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        # Try to salvage JSON if the model added extra text around it
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw[start:end+1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    # Fallback if the model didn't return valid JSON
    return {
        "summary": [raw],
        "key_terms": [],
        "unit_conversions": [],
        "clarifying_question": ""
    }


@router.post("/generate_info_structured")
async def generate_info_structured_endpoint(request: LLMRequest):
    """
    FastAPI endpoint to generate structured information from user text.
    Returns a JSON object suitable for consistent UI rendering.
    """
    try:
        info = generate_info_from_llm_structured(request.content)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
