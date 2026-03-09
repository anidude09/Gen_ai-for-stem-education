"""
llm.py

FastAPI router for LLMs. Uses the `construction_llm_explainer` package.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from construction_llm_explainer import explain_term, build_drawing_context_str
from services.rag_service import rag_service

router = APIRouter()

class LLMRequest(BaseModel):
    content: str
    drawing_context: Optional[Dict[str, Any]] = None

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

    # Call the LLM Explainer package directly
    parsed = explain_term(
        text=text,
        rag_context=rag_context,
        drawing_context_str=drawing_context_str
    )
    
    # Inject front-end specific keys (like images) that the generic package shouldn't know about
    if image_url:
        parsed["dict_image"] = image_url
        
    return parsed

@router.post("/generate_info_structured")
async def generate_info_structured_endpoint(request: LLMRequest):
    try:
        info = generate_info_from_llm_structured(
            request.content,
            drawing_context=request.drawing_context,
        )
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
