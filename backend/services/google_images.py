import os
from typing import List, Dict

import httpx
from dotenv import load_dotenv


load_dotenv()

GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX")


async def search_construction_images(query: str, max_results: int = 3) -> List[Dict]:
    """
    Call Google Programmable Search (Custom Search JSON API) for images
    related to a construction concept.

    Returns a list of dicts with:
      - image_url
      - thumbnail_url
      - page_url
      - title
      - source
    """
    if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_CX:
        # Graceful no-op if keys are not configured
        return []

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_CSE_API_KEY,
        "cx": GOOGLE_CSE_CX,
        "q": query,
        "searchType": "image",
        "num": max_results,
        "safe": "active",
        # Optionally restrict to more reusable images:
        # "rights": "cc_publicdomain|cc_attribute|cc_sharealike",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        # Log and return empty list rather than failing the whole request
        print(f"Google image search error: {e}")
        return []

    items = data.get("items") or []
    images: List[Dict] = []

    for item in items:
        link = item.get("link")
        if not link:
            continue

        title = item.get("title") or ""
        image_info = item.get("image") or {}
        thumb = image_info.get("thumbnailLink") or link
        context_link = image_info.get("contextLink") or link

        images.append(
            {
                "image_url": link,
                "thumbnail_url": thumb,
                "page_url": context_link,
                "title": title,
                "source": item.get("displayLink") or "",
            }
        )

    return images


