"""
llm.py

FastAPI router for LLMs. Uses the `construction_llm_explainer` package.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from construction_llm_explainer import explain_term, build_drawing_context_str
from services.rag_service import rag_service
from services.google_images import search_construction_images
from prompts import llm_system_prompt, llm_user_prompt

router = APIRouter()

class LLMRequest(BaseModel):
    content: str
    drawing_context: Optional[Dict[str, Any]] = None
    include_images: bool = False

def generate_info_from_llm_structured(text: str, drawing_context: dict = None) -> dict:
    """Wrapper that resolves context through RAG before calling the LLM package."""
    # RAG context resolution
    term_entry = rag_service.get_term_entry(text)
    if term_entry:
        page = term_entry.get("page", "N/A")
        definition = term_entry.get("definition", "")
        rag_context = f"--- Source: RSMeans Dictionary (Page {page}) ---\n{definition}"
        image_path = term_entry.get("image")
    else:
        rag_context = rag_service.get_context(text)
        image_path = None

    image_url = None
    if image_path:
        if image_path.startswith("images/"):
            image_url = "/dict-images/" + image_path[7:]
        else:
            image_url = "/dict-images/" + image_path

    # Construct drawing context via package helper
    drawing_context_str = build_drawing_context_str(drawing_context)

    # Call the LLM Explainer package with prompts from central prompts.py
    parsed = explain_term(
        text=text,
        rag_context=rag_context,
        drawing_context_str=drawing_context_str,
        system_prompt=llm_system_prompt(rag_context, drawing_context_str),
        user_prompt=llm_user_prompt(text),
    )
    
    # Inject front-end specific keys (like images) that the generic package shouldn't know about
    if image_url:
        parsed["dict_image"] = image_url
        
    return parsed

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

@router.post("/generate_info_structured")
async def generate_info_structured_endpoint(request: LLMRequest):
    try:
        info = generate_info_from_llm_structured(
            request.content,
            drawing_context=request.drawing_context,
        )
        
        if request.include_images:
            query = _build_image_query(request.content, info)
            images_raw = await search_construction_images(query, max_results=3)
            info["images"] = images_raw
            
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
