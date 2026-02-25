"""
vlm.py

VLM analysis route using OpenAI GPT-4o Vision.

POST /vlm/analyze
  - Accepts an image file + optional crop coordinates (x, y, w, h in natural image pixels).
  - If crop params are provided, crops that region from the image first.
  - Resizes to at most MAX_LONG_SIDE pixels on the longest dimension before encoding to base64.
    (Construction drawings are typically 10800x7201 — we reduce to ~2048x1366 which is
     GPT-4o's effective high-detail tile ceiling. Sending larger wastes tokens with no gain.)
  - Calls GPT-4o Vision and returns a structured educational analysis.

Returns JSON:
  {
    "mode":           "full" | "region",
    "drawing_type":   str,
    "summary":        [str, ...],          # 2-4 plain-language bullets
    "text_labels":    [{text, category, explanation}, ...],
    "detail_circles": [{number, page_reference, meaning}, ...],
    "symbols":        [{type, description}, ...],
    "student_tip":    str
  }
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

load_dotenv()

# ── OpenAI client (lazy init so the app still starts if key is missing) ────────
_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI  # type: ignore
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set in .env")
            _openai_client = OpenAI(api_key=api_key)
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai>=1.30.0"
            )
    return _openai_client


# ── Constants ─────────────────────────────────────────────────────────────────
# GPT-4o high-detail mode tiles the image as 512px squares after fitting to
# a 2048×2048 bounding box. Sending anything larger gives no extra information
# but burns extra input tokens (and costs more). 2048 is the sweet spot.
MAX_LONG_SIDE = 2048

VLM_MODEL = "gpt-4o"

# ── VLM CSV log ──────────────────────────────────────────────────────
# One row written per GPT-4o Vision call.  Stored next to activity_log.csv
# so both files can be joined on session_id.
_VLM_LOG_PATH: Path = Path(__file__).resolve().parent.parent / "vlm_log.csv"
_VLM_LOG_FIELDS = [
    "timestamp_utc",
    "session_id",
    "mode",           # full | region
    "crop_x", "crop_y", "crop_w", "crop_h",
    "image_sent_w", "image_sent_h",   # pixels actually sent to GPT-4o
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "response_json",  # full JSON string returned by GPT-4o
]


def _ensure_vlm_log() -> None:
    """Create vlm_log.csv with header row if it doesn't exist yet."""
    if not _VLM_LOG_PATH.exists():
        _VLM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _VLM_LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=_VLM_LOG_FIELDS).writeheader()


# Initialise once at import time (same pattern as activity_log.py)
_ensure_vlm_log()


def _write_vlm_log(
    *,
    session_id: str,
    mode: str,
    crop_x: Optional[int],
    crop_y: Optional[int],
    crop_w: Optional[int],
    crop_h: Optional[int],
    image_sent_size: tuple[int, int],
    usage,               # openai CompletionUsage object
    response_json: dict,
) -> None:
    """Append one row to vlm_log.csv."""
    row = {
        "timestamp_utc":    datetime.now(timezone.utc).isoformat(),
        "session_id":       session_id or "",
        "mode":             mode,
        "crop_x":           crop_x if crop_x is not None else "",
        "crop_y":           crop_y if crop_y is not None else "",
        "crop_w":           crop_w if crop_w is not None else "",
        "crop_h":           crop_h if crop_h is not None else "",
        "image_sent_w":     image_sent_size[0],
        "image_sent_h":     image_sent_size[1],
        "prompt_tokens":    usage.prompt_tokens,
        "completion_tokens":usage.completion_tokens,
        "total_tokens":     usage.total_tokens,
        "response_json":    json.dumps(response_json, ensure_ascii=False),
    }
    with _VLM_LOG_PATH.open("a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=_VLM_LOG_FIELDS).writerow(row)
    print(
        f"[VLM] Logged to vlm_log.csv — {usage.total_tokens} tokens, "
        f"mode={mode}, session={session_id or 'anon'}"
    )

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

router = APIRouter()


# ── Image helpers ──────────────────────────────────────────────────────────────

def _resize_for_vlm(img: Image.Image) -> Image.Image:
    """
    Resize image so its longest side is at most MAX_LONG_SIDE pixels.
    Preserves aspect ratio. Returns the image unchanged if already small enough.
    """
    w, h = img.size
    long_side = max(w, h)
    if long_side <= MAX_LONG_SIDE:
        return img
    scale = MAX_LONG_SIDE / long_side
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    print(f"[VLM] Resizing {w}x{h} → {new_w}x{new_h} for GPT-4o Vision")
    return img.resize((new_w, new_h), Image.LANCZOS)


def _encode_image(img: Image.Image) -> str:
    """Encode a PIL Image to PNG base64 string."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _parse_vlm_response(raw: str) -> dict:
    """Parse the VLM JSON response, with fallback on malformed output."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from surrounding noise
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
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


# ── Route ──────────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def vlm_analyze(
    file: UploadFile = File(...),
    x: Optional[int] = Form(None),
    y: Optional[int] = Form(None),
    w: Optional[int] = Form(None),
    h: Optional[int] = Form(None),
    session_id: Optional[str] = Form(None),
):
    """
    Analyze a construction drawing (or a cropped region) with GPT-4o Vision.

    Crop params (x, y, w, h) are in NATURAL image pixels (before any display
    scaling). If all four are provided, only that region is sent to the VLM.
    """
    try:
        client = _get_openai_client()
    except RuntimeError as err:
        return JSONResponse(status_code=503, content={"error": str(err)})

    try:
        image_bytes = await file.read()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return JSONResponse(
            status_code=400, content={"error": f"Failed to decode image: {exc}"}
        )

    # Determine mode and crop if needed
    is_region = all(v is not None for v in [x, y, w, h])
    mode = "region" if is_region else "full"

    if is_region:
        img_w, img_h = img.size
        crop_x = max(0, min(x, img_w))
        crop_y = max(0, min(y, img_h))
        crop_x2 = max(0, min(x + w, img_w))
        crop_y2 = max(0, min(y + h, img_h))
        if crop_x2 <= crop_x or crop_y2 <= crop_y:
            return JSONResponse(
                status_code=400, content={"error": "Crop region is empty or invalid."}
            )
        img = img.crop((crop_x, crop_y, crop_x2, crop_y2))
        print(f"[VLM] Cropped to ({crop_x},{crop_y},{crop_x2},{crop_y2})")

    # Resize to GPT-4o's effective resolution ceiling
    img = _resize_for_vlm(img)
    b64 = _encode_image(img)

    user_message = (
        "Analyze this construction drawing region and return the JSON object as instructed."
        if is_region
        else "Analyze this full construction drawing and return the JSON object as instructed."
    )

    try:
        print(f"[VLM] Calling GPT-4o Vision (mode={mode}, size={img.size})")
        completion = client.chat.completions.create(
            model=VLM_MODEL,
            temperature=0.2,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
        )
        raw = completion.choices[0].message.content.strip()
        print(
            f"[VLM] Response received ({completion.usage.total_tokens} tokens total)"
        )
    except Exception as exc:
        print(f"[VLM] OpenAI API error: {exc}")
        return JSONResponse(
            status_code=502, content={"error": f"VLM API call failed: {exc}"}
        )

    result = _parse_vlm_response(raw)
    result["mode"] = mode

    # ── Write to vlm_log.csv ──────────────────────────────────────────
    try:
        _write_vlm_log(
            session_id=session_id or "",
            mode=mode,
            crop_x=x, crop_y=y, crop_w=w, crop_h=h,
            image_sent_size=img.size,
            usage=completion.usage,
            response_json=result,
        )
    except Exception as log_err:
        # Never let logging failure break the API response
        print(f"[VLM] Warning: failed to write vlm_log.csv: {log_err}")

    return result
