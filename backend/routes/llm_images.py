"""
llm_images.py

New router that combines the existing structured LLM explanation with
Google image search results, without modifying the original llm routes.
"""

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .llm import LLMRequest, generate_info_from_llm_structured
from services.google_images import search_construction_images


router = APIRouter()


class ImageInfo(BaseModel):
    image_url: str
    thumbnail_url: str
    page_url: str
    title: str
    source: str


class LLMWithImagesResponse(BaseModel):
    summary: List[str]
    key_terms: List[Dict[str, Any]]
    unit_conversions: List[Dict[str, Any]]
    clarifying_question: str
    images: List[ImageInfo]


def _build_image_query(snippet: str, info: Dict[str, Any]) -> str:
    """
    Construct a construction-focused image search query, preferring key_terms
    from the LLM output and falling back to the raw snippet.
    """
    key_terms = info.get("key_terms") or []
    if key_terms:
        terms = [kt.get("term", "") for kt in key_terms if kt.get("term")]
        # Use at most the first two terms
        terms = [t for t in terms if t][:2]
        if terms:
            return " ".join(terms) + " construction plans related images"

    snippet_clean = (snippet or "").strip().replace("\n", " ")
    if len(snippet_clean) > 160:
        snippet_clean = snippet_clean[:160]
    return snippet_clean + " civil engineering diagrams related images"


@router.post(
    "/explain_with_images",
    response_model=LLMWithImagesResponse,
)
async def explain_with_images(request: LLMRequest):
    """
    Generate a structured explanation from the LLM and augment it with
    a small set of relevant construction images from Google search.

    This endpoint is intentionally separate from the existing LLM routes so
    that the original behavior remains unchanged.
    """
    try:
        # 1) Structured LLM interpretation of the snippet
        info = generate_info_from_llm_structured(request.content)

        # 2) Image search query
        query = _build_image_query(request.content, info)

        # 3) Fetch related images (non-fatal if search fails)
        images_raw = await search_construction_images(query, max_results=3)

        # 4) Shape response; if Google failed, images_raw may be empty
        return {
            "summary": info.get("summary") or [],
            "key_terms": info.get("key_terms") or [],
            "unit_conversions": info.get("unit_conversions") or [],
            "clarifying_question": info.get("clarifying_question") or "",
            "images": images_raw,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


