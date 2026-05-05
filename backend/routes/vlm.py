"""
vlm.py

VLM analysis route using OpenAI GPT-4o Vision.
Uses the extracted construction-vlm-analyzer package.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from construction_vlm_analyzer import analyze_drawing
from prompts import VLM_MAX_LONG_SIDE, VLM_DETAIL, VLM_FORMAT, VLM_SYSTEM_PROMPT, vlm_user_prompt

# ── VLM CSV log ──────────────────────────────────────────────────────
_VLM_LOG_PATH: Path = Path(__file__).resolve().parent.parent / "vlm_log.csv"
_VLM_LOG_FIELDS = [
    "timestamp_utc",
    "session_id",
    "mode",           # full | region
    "crop_x", "crop_y", "crop_w", "crop_h",
    "image_sent_w", "image_sent_h",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "response_json",
]

def _ensure_vlm_log() -> None:
    if not _VLM_LOG_PATH.exists():
        _VLM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _VLM_LOG_PATH.open("w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=_VLM_LOG_FIELDS).writeheader()

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
    usage,
    response_json: dict,
) -> None:
    """Append one row to vlm_log.csv."""
    import json
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
        "prompt_tokens":    usage.prompt_tokens if usage else 0,
        "completion_tokens":usage.completion_tokens if usage else 0,
        "total_tokens":     usage.total_tokens if usage else 0,
        "response_json":    json.dumps(response_json, ensure_ascii=False),
    }
    with _VLM_LOG_PATH.open("a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=_VLM_LOG_FIELDS).writerow(row)
    print(
        f"[VLM route] Logged to vlm_log.csv — {usage.total_tokens if usage else 0} tokens, "
        f"mode={mode}, session={session_id or 'anon'}"
    )


# ── Route ──────────────────────────────────────────────────────────────────────

router = APIRouter()

@router.post("/analyze")
async def vlm_analyze(
    file: UploadFile = File(...),
    x: Optional[int] = Form(None),
    y: Optional[int] = Form(None),
    w: Optional[int] = Form(None),
    h: Optional[int] = Form(None),
    session_id: Optional[str] = Form(None),
    detail_context: Optional[str] = Form(None),
):
    try:
        from io import BytesIO
        image_bytes = await file.read()
        
        try:
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            return JSONResponse({"error": f"Invalid image format: {e}"}, status_code=400)

        crop_region = None
        mode = "full"
        if all(v is not None for v in [x, y, w, h]):
            crop_region = (x, y, w, h)
            mode = "region"

        # DELEGATE TO VLM ANALYZER PACKAGE
        result = analyze_drawing(
            img,
            crop_region=crop_region,
            system_prompt=VLM_SYSTEM_PROMPT,
            user_prompt=vlm_user_prompt(detail_context),
            detail=VLM_DETAIL,
            max_long_side=VLM_MAX_LONG_SIDE,
            image_format=VLM_FORMAT,
        )

        # Logging
        analysis = result["analysis"]
        meta = result["metadata"]
        _write_vlm_log(
            session_id=session_id,
            mode=mode,
            crop_x=x, crop_y=y, crop_w=w, crop_h=h,
            image_sent_size=meta["image_sent_size"],
            usage=meta["usage"],
            response_json=analysis,
        )

        # Prepend drawing mode hint for the frontend
        if mode == "region":
            analysis["drawing_type"] = "Region of " + analysis.get("drawing_type", "Drawing")

        return analysis

    except RuntimeError as e:
        print(f"[VLM route] Error: {e}")
        error_msg = str(e)
        if "OPENAI_API_KEY" in error_msg:
            return JSONResponse({"error": "OPENAI_API_KEY is missing."}, status_code=500)
        return JSONResponse({"error": error_msg}, status_code=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"VLM analysis failed: {e}"}, status_code=500)
