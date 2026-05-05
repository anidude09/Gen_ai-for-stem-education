"""
chat.py

Provides the `/chat` route for communicating with the interactive plan assistant.
Streams back responses using Server-Sent Events (SSE) so the UI feels responsive.
"""

import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from langchain_core.messages import AIMessageChunk, AIMessage, ToolMessage

from services.agent_service import llm, memory, SYSTEM_PROMPT
from services.agent_tools import get_agent_tools
from services.image_cache import store as img_store, get as img_get, cache_key, resolve_server_path
from langgraph.prebuilt import create_react_agent
from construction_vlm_analyzer import analyze_drawing
from prompts import CTX_MAX_LONG_SIDE, CTX_DETAIL, CTX_FORMAT, VLM_SYSTEM_PROMPT, vlm_user_prompt
from io import BytesIO
from PIL import Image

router = APIRouter()

# In-memory cache for global VLM context keyed by page_session_id
_global_context_cache: dict[str, str] = {}

@router.post("/context")
async def build_context(
    file: Optional[UploadFile] = File(None),
    page_session_id: str = Form(...),
    page_label: str = Form("Drawing"),
    server_image_path: Optional[str] = Form(None),
):
    """
    Builds VLM context for a drawing page and appends it to the session's context cache.
    Called for the main image on upload and for each navigated page.

    For server-hosted pages (/images/*.png), pass server_image_path instead of uploading the file —
    the backend reads the bytes directly from disk.
    """
    try:
        ck = cache_key(page_session_id, page_label)
        image_bytes = img_get(ck)

        if image_bytes is None:
            if server_image_path:
                image_bytes = resolve_server_path(server_image_path)
                if image_bytes:
                    print(f"[chat/context] Read {len(image_bytes)//1024}KB from disk: {server_image_path}")
            if image_bytes is None:
                if file is None:
                    return JSONResponse({"status": "error", "detail": "No image source"}, status_code=400)
                image_bytes = await file.read()
            img_store(ck, image_bytes)

        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        vlm_res = analyze_drawing(
            img,
            system_prompt=VLM_SYSTEM_PROMPT,
            user_prompt=vlm_user_prompt(),
            detail=CTX_DETAIL,
            max_long_side=CTX_MAX_LONG_SIDE,
            image_format=CTX_FORMAT,
        )
        page_ctx = json.dumps(vlm_res.get("analysis", vlm_res))

        section = f"--- PAGE: {page_label} ---\n{page_ctx}"
        if page_session_id in _global_context_cache:
            _global_context_cache[page_session_id] += f"\n\n{section}"
        else:
            _global_context_cache[page_session_id] = section

        return JSONResponse({"status": "ok", "analysis": vlm_res.get("analysis", vlm_res)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

@router.post("/")
async def chat_endpoint(
    file: UploadFile = File(...),
    message: str = Form(...),
    page_session_id: str = Form(...)
):
    """
    Accepts an image, a chat message, and a session ID.
    Returns a streaming text/event-stream response.
    """
    image_bytes = await file.read()
    
    async def event_generator():
        try:
            cached_ctx = _global_context_cache.get(page_session_id)
            tools = get_agent_tools(image_bytes, global_ctx=cached_ctx)
            agent_executor = create_react_agent(
                model=llm,
                tools=tools,
                checkpointer=memory
            )

            config = {
                "configurable": {"thread_id": page_session_id},
                "recursion_limit": 15
            }

            input_messages = [("system", SYSTEM_PROMPT)]

            # Inject cached global context into the first conversation turn

            if cached_ctx:
                state = agent_executor.get_state(config)
                existing = state.values.get("messages", []) if state and state.values else []
                if not existing:
                    input_messages.append(("system", f"GLOBAL DRAWING ARCHITECTURAL CONTEXT (reference this for overall layout understanding):\n{cached_ctx}"))

            input_messages.append(("user", message))
            
            # Stream using stream_mode="updates" which gives us node-level updates
            async for event in agent_executor.astream({"messages": input_messages}, config=config, stream_mode="updates"):
                for node_name, node_data in event.items():
                    msgs = node_data.get("messages", [])
                    for msg in msgs:
                        if isinstance(msg, (AIMessage, AIMessageChunk)):
                            # Emit text content
                            if msg.content:
                                payload = {"type": "text", "content": str(msg.content)}
                                yield f"data: {json.dumps(payload)}\n\n"
                            
                            # Emit tool call starts
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tool_name = tc.get("name", "unknown")
                                    payload = {"type": "tool_start", "name": tool_name}
                                    yield f"data: {json.dumps(payload)}\n\n"
                                    
                        elif isinstance(msg, ToolMessage):
                            if msg.name == "highlight_shapes_on_canvas":
                                try:
                                    data = json.loads(msg.content)
                                    if data.get("__agent_draw_action__"):
                                        yield f"data: {json.dumps({'type': 'draw_shapes', 'data': data})}\n\n"
                                except:
                                    pass
                            payload = {"type": "tool_end", "name": msg.name}
                            yield f"data: {json.dumps(payload)}\n\n"

            yield "data: [DONE]\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
