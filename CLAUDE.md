# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI-powered tool for analyzing construction drawings. Users upload construction plan images; the app detects labeled callouts (circles/text), explains construction terms via RAG + GPT-4o, supports vision analysis of drawing regions, and provides an agentic chat interface that can reason over drawings using tools.

## Development Commands

### Frontend (app/)
```bash
cd app
npm install          # install deps
npm run dev          # dev server at http://localhost:5173
npm run build        # build to app/dist/
npm run lint         # ESLint check
```

### Backend (backend/)
```bash
# Create and activate venv first
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.\.venv\Scripts\Activate.ps1     # Windows

pip install -r backend/requirements.txt

# Install all local packages in editable mode
pip install -e packages/construction_ocr
pip install -e packages/construction_circle_detector
pip install -e packages/construction_llm_explainer
pip install -e packages/construction_plan_rag
pip install -e packages/construction_vlm_analyzer

# Run backend
cd backend
uvicorn app:app --host 127.0.0.1 --port 8001

# Or use the launcher (starts backend + opens browser):
python launcher.py
```

### Docker
```bash
docker compose build   # ~10-15 min first time
docker compose up
docker compose down
docker compose logs -f
```

## Environment Variables

Copy `.env.example` to `backend/.env`:
- `OPENAI_API_KEY` — required (GPT-4o text + vision)
- `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX` — required (Google image search)
- `GROQ_API_KEY` — optional (fallback LLM)

## Architecture

```
app/          React 19 + Vite frontend
backend/      FastAPI server (port 8001)
packages/     5 modular Python packages (installed editable into backend)
data/         NOT in repo — RSMeans dictionary PDFs + extracted terms.json + images
```

### Request Flow

1. User uploads a construction drawing image in the browser → new `pageSessionId` UUID created.
2. Frontend POSTs image to `/detect/` → backend calls `construction_ocr` + `construction_circle_detector` packages → returns detected circles and text labels.
3. App automatically calls `/chat/context` to build and cache VLM context for the drawing (used by agent).
4. User clicks a detected term → frontend POSTs to `/llm/generate_info_structured` → backend calls `construction_plan_rag` (exact JSON lookup + ChromaDB vector search) then `construction_llm_explainer` (GPT-4o) → returns structured explanation.
5. Vision analysis (VLMPanel) POSTs to `/vlm/analyze` → `construction_vlm_analyzer` (GPT-4o Vision).
6. Agent chat (AgentChatPanel) POSTs to `/chat/` → `agent_service.py` orchestrates a LangGraph ReAct loop via `agent_tools.py`, streaming SSE events back to the frontend.

### Local Python Packages

| Package | Purpose |
|---|---|
| `construction_ocr` | PaddleOCR wrapper for text detection |
| `construction_circle_detector` | OpenCV contour + Hough circle detection |
| `construction_llm_explainer` | GPT-4o (+ Groq fallback) term explanations |
| `construction_plan_rag` | ChromaDB vector search + exact JSON lookup against RSMeans dictionary |
| `construction_vlm_analyzer` | GPT-4o Vision for full/partial drawing analysis |

### Frontend–Backend URL Config

`app/src/config.js` controls `API_BASE_URL`:
- Dev: `http://localhost:8001`
- Prod (Docker): same-origin (FastAPI serves `app/dist/` as static files)

### Key Backend Files

- `backend/app.py` — FastAPI setup, CORS (`allow_origins=["*"]`), route registration, static file + frontend serving
- `backend/prompts.py` — centralized LLM prompts, image sizing constants, VLM/agent config
- `backend/routes/detect.py` — POST `/detect/`: circle + OCR detection; caches image bytes in `image_cache`
- `backend/routes/llm.py` — POST `/llm/generate_info_structured`: RAG lookup + GPT-4o term explanation
- `backend/routes/vlm.py` — POST `/vlm/analyze`, `/vlm/analyze_region`: vision analysis with CSV logging
- `backend/routes/chat.py` — POST `/chat/context` (build + cache VLM context), POST `/chat/` (SSE streaming agent)
- `backend/routes/auth.py` — POST `/login`, `/logout`, GET `/session/:id`: SQLite session management
- `backend/routes/activity_log.py` — POST `/activity/log`: user event CSV logging
- `backend/routes/regions_detect.py` — region-specific detection endpoint
- `backend/services/rag_service.py` — thin wrapper initializing `construction_plan_rag`
- `backend/services/agent_service.py` — LangGraph ReAct agent with GPT-4o + MemorySaver checkpointing
- `backend/services/agent_tools.py` — 6 LangChain `@tool` definitions: `search_dictionary`, `scan_for_circles`, `scan_for_text`, `analyze_drawing_region`, `search_internet_for_images`, `highlight_shapes_on_canvas`
- `backend/services/image_cache.py` — in-memory image byte cache keyed by `(page_session_id, page_label)`; resolves `/images/*.png` from disk
- `backend/services/google_images.py` — Google Custom Search API integration

### Key Frontend Files

- `app/src/App.jsx` — main component: multi-view state (`main` + per-page), session management, context-building effects, 3-column layout (sidebar | canvas | chat)
- `app/src/components/ImageCanvas.jsx` — canvas rendering and user interaction
- `app/src/components/ShapeOverlay.jsx` — renders detected circles/text overlays; accepts agent draw commands
- `app/src/components/Popup.jsx` — term explanation popup (calls `/llm/`)
- `app/src/components/AgentChatPanel.jsx` — 480px streaming chat sidebar; parses SSE events (`text`, `tool_start`, `tool_end`, `draw_shapes`, `error`); displays tool execution status
- `app/src/components/VLMPanel.jsx` — VLM analysis panel
- `app/src/components/ImageUploader.jsx` — file upload trigger
- `app/src/components/ZoomControls.jsx` — zoom UI (1x–3x, step 0.25)
- `app/src/hooks/useZoom.jsx` — zoom state management
- `app/src/hooks/useautoLogout.jsx` — auto-logout after 50 minutes idle
- `app/src/hooks/useLogout.jsx` — logout with session cleanup
- `app/src/utils/activityLogger.js` — logs interactions to `/activity/log` (for research tracking)
- `app/src/utils/scaleShapes.js` — scales detection coordinates to viewport dimensions

### Context Building & Agent Flow

1. On image upload, a new `pageSessionId` UUID is created.
2. App calls `/chat/context` which runs VLM analysis and caches the result server-side in `_global_context_cache[pageSessionId]`.
3. When user navigates to a detail page (red circle callout), the same process runs for that page's image.
4. On agent message, `/chat/` reads cached context, injects it as system message, runs LangGraph ReAct loop.
5. Agent streams SSE: text chunks, tool start/end events, and `draw_shapes` commands that trigger canvas highlights.

### Data (not in repo)

The `data/` directory must be manually placed. It contains:
- `RSMeans_Illustrated_Construction_Dictionary/terms.json` — exact-lookup dictionary
- `RSMeans_Illustrated_Construction_Dictionary/images/` — page images referenced by RAG
- PDF source files

The RAG package builds a ChromaDB index (persisted to `backend/chroma_db/`) from these files on first run.

## Notes

- No test suite exists; there are no pytest or other test configs.
- `backend/sessions.db` (SQLite), `backend/activity_log.csv`, and `backend/vlm_log.csv` are runtime artifacts, not committed.
- `backend/routes/llm_images.py` is deleted on this branch (`feature/agentic`); do not re-add it.
- Docker uses CUDA 11.8 but gracefully falls back to CPU if no GPU is present.
- Key Python dependencies: FastAPI 0.111, LangChain 0.1.12, LangGraph, LangChain-OpenAI 0.1, ChromaDB 0.4.24, OpenCV 4.8, PaddleOCR (via `construction_ocr`), sentence-transformers 2.7.
