"""
analyzer.py — Core entrypoint for calling GPT-4o Vision API.
"""

from __future__ import annotations

import os
from typing import Optional
from PIL import Image

from construction_vlm_analyzer.image_utils import resize_for_vlm, encode_image, MAX_LONG_SIDE
from construction_vlm_analyzer.prompts import parse_vlm_response

_openai_client = None


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI  # type: ignore
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set in environment or .env")
            _openai_client = OpenAI(api_key=api_key)
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai>=1.30.0"
            )
    return _openai_client


def analyze_drawing(
    img: Image.Image,
    crop_region: Optional[tuple[int, int, int, int]] = None,
    detail_context: Optional[str] = None,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    detail: str = "high",
    max_long_side: int = MAX_LONG_SIDE,
    image_format: str = "PNG",
) -> dict:
    """
    Analyze a construction drawing with GPT-4o Vision.

    Args:
        system_prompt: Override the default VLM system prompt.
        user_prompt:   Override the default user message (detail_context is ignored when set).
        detail:        OpenAI detail level — "high", "low", or "auto".
        max_long_side: Resize the image so its longest side is at most this many pixels.
        image_format:  "PNG" or "JPEG". JPEG reduces upload size; tokens are tile-based.
    """
    client = get_openai_client()

    if crop_region is not None:
        x, y, w, h = crop_region
        if w > 0 and h > 0:
            print(f"[vlm_analyzer] Cropped to ({x},{y},{x+w},{y+h})")
            img = img.crop((x, y, x + w, y + h))

    img_resized = resize_for_vlm(img, max_long_side=max_long_side)
    base64_img, mime_type = encode_image(img_resized, fmt=image_format)

    # Build user message
    if user_prompt is not None:
        user_text = user_prompt
    else:
        user_text = "Analyze this drawing. Return ONLY pure JSON mapping to the requested schema. Do not use markdown backticks."
        if detail_context:
            user_text += (
                f"\n\nContext: {detail_context}. "
                "Focus your analysis on explaining what this detail page shows "
                "and how it relates to the referenced detail circle from the main drawing."
            )

    if system_prompt is None:
        raise ValueError("system_prompt is required — pass it from backend/prompts.py")

    print(f"[vlm_analyzer] Calling GPT-4o Vision (size={img_resized.size}, detail={detail}, fmt={image_format})")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_img}",
                            "detail": detail,
                        }
                    }
                ]
            }
        ],
        max_tokens=2500,
        temperature=0.2,
    )

    raw_response = response.choices[0].message.content or ""
    print(f"[vlm_analyzer] Response received ({response.usage.total_tokens} tokens)")

    parsed_json = parse_vlm_response(raw_response)

    return {
        "analysis": parsed_json,
        "metadata": {
            "image_sent_size": img_resized.size,
            "usage": response.usage,
            "raw_response": raw_response
        }
    }
