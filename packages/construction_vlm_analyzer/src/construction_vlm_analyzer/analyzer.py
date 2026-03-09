"""
analyzer.py — Core entrypoint for calling GPT-4o Vision API.
"""

from __future__ import annotations

import os
from typing import Optional
from PIL import Image

from construction_vlm_analyzer.image_utils import resize_for_vlm, encode_image
from construction_vlm_analyzer.prompts import SYSTEM_PROMPT, parse_vlm_response

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
    crop_region: Optional[tuple[int, int, int, int]] = None
) -> dict:
    """
    Analyze a structural/construction drawing with GPT-4o Vision.
    
    Args:
        img: A PIL Image of the drawing.
        crop_region: Optional (x, y, w, h) to crop the image before analysis.
    
    Returns:
        dict: A structured dictionary containing the analysis, plus metadata
              like raw response string and token usage.
    """
    client = get_openai_client()

    if crop_region is not None:
        x, y, w, h = crop_region
        if w > 0 and h > 0:
            print(f"[vlm_analyzer] Cropped to ({x},{y},{x+w},{y+h})")
            img = img.crop((x, y, x + w, y + h))

    img_resized = resize_for_vlm(img)
    base64_img = encode_image(img_resized)

    print(f"[vlm_analyzer] Calling GPT-4o Vision (size={img_resized.size})")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this drawing. Return ONLY pure JSON mapping to the requested schema. Do not use markdown backticks."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_img}",
                            "detail": "high"
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
    
    # Return structured output along with usage metadata for backend logging
    return {
        "analysis": parsed_json,
        "metadata": {
            "image_sent_size": img_resized.size,
            "usage": response.usage,
            "raw_response": raw_response
        }
    }
