"""
agent_tools.py

Wraps our existing pipeline functions into LangChain `@tool` definitions.
We use a factory function `get_agent_tools(image_bytes)` so the tools
implicitly act on the currently uploaded image without needing to pass
image data through the LLM context.
"""

import json
from io import BytesIO
from PIL import Image

from langchain_core.tools import tool

from construction_circle_detector import detect_circles_from_bytes
from construction_ocr.pipeline import detect_text_from_bytes
from construction_vlm_analyzer import analyze_drawing
from services.rag_service import rag_service
from services.google_images import search_construction_images
from prompts import VLM_SYSTEM_PROMPT, vlm_user_prompt, AGENT_MAX_LONG_SIDE, AGENT_DETAIL, AGENT_FORMAT

def get_agent_tools(image_bytes: bytes, global_ctx: str = None) -> list:
    """Returns a list of LangChain tools bound to the current image bytes."""
    
    @tool
    def search_dictionary(query: str) -> str:
        """Looks up a construction term or abbreviation in the RSMeans Illustrated Construction Dictionary and returns the definition."""
        try:
            context = rag_service.get_context(query)
            if not context:
                return f"No definition found for '{query}'."
            return context
        except Exception as e:
            return f"Error searching dictionary: {str(e)}"

    @tool
    def scan_for_circles() -> str:
        """Finds all callout circles/reference symbols in the current drawing. 
        Returns a JSON payload with bounding box coordinates for each circle."""
        try:
            circles = detect_circles_from_bytes(image_bytes)
            if not circles:
                return "No circles or reference callouts detected."
            return json.dumps(circles)
        except Exception as e:
            return f"Error detecting circles: {str(e)}"

    @tool
    def scan_for_text() -> str:
        """Extracts all text from the current drawing using OCR. 
        Returns a JSON array containing the detected text blocks and their bounding boxes."""
        try:
            texts = detect_text_from_bytes(image_bytes)
            if not texts:
                return "No text detected."
            return json.dumps(texts)
        except Exception as e:
            return f"Error running OCR: {str(e)}"

    @tool
    def analyze_drawing_region(x: int = None, y: int = None, w: int = None, h: int = None, detail_context: str = None) -> str:
        """Visually analyzes the drawing using GPT-4o Vision.
        Provide x, y, w, h to crop and analyze a specific region.
        Leave x, y, w, h blank to analyze the entire full-page drawing.
        Pass detail_context (optional) if you want to explain this drawing in relation to a parent reference."""
        try:
            crop_region = None
            if x is not None and y is not None and w is not None and h is not None:
                crop_region = (x, y, w, h)

            # Reuse cached full-image analysis to avoid a redundant VLM call
            if crop_region is None and global_ctx:
                return global_ctx

            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            result = analyze_drawing(
                img,
                crop_region=crop_region,
                system_prompt=VLM_SYSTEM_PROMPT,
                user_prompt=vlm_user_prompt(detail_context),
                detail=AGENT_DETAIL,
                max_long_side=AGENT_MAX_LONG_SIDE,
                image_format=AGENT_FORMAT,
            )
            return json.dumps(result.get("analysis", result))
        except Exception as e:
            return f"Error analyzing image with VLM: {str(e)}"
            
    @tool
    async def search_internet_for_images(query: str) -> str:
        """Searches Google for real-world construction images related to the query. 
        Returns markdown containing image URLs, titles, and sources. Use this when the user might benefit from seeing what a material or component looks like."""
        try:
            images = await search_construction_images(query, max_results=3)
            if not images:
                return "No images found on Google."
            # Agents love markdown, so let's format it for GPT-4o!
            result = f"Images found for '{query}':\n"
            for index, img in enumerate(images):
                result += f"{index+1}. Title: {img['title']}\nURL: ![image_{index}]({img['image_url']})\nSource: {img['source']}\n\n"
            return result
        except Exception as e:
            return f"Error searching Google Images: {str(e)}"

    @tool
    def highlight_shapes_on_canvas(rectangles: list[dict] = None, circles: list[dict] = None) -> str:
        """
        Draws highlighted rectangles or circles on the user's screen.
        rectangles format: [{"x1": int, "y1": int, "x2": int, "y2": int, "label": str, "color": str}]
        circles format: [{"x": int, "y": int, "r": int, "label": str, "color": str}]
        Use this to visually point out specific components to the user.
        """
        payload = {
            "__agent_draw_action__": True,
            "rectangles": rectangles or [],
            "circles": circles or []
        }
        return json.dumps(payload)

    return [search_dictionary, scan_for_circles, scan_for_text, analyze_drawing_region, search_internet_for_images, highlight_shapes_on_canvas]
