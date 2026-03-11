# ============================================================
# Stage 1: Build the React frontend
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /build/app
COPY app/package.json app/package-lock.json ./
RUN npm ci --prefer-offline
COPY app/ ./
RUN npm run build          
# Output: /build/app/dist/

# ============================================================
# Stage 2: Python backend + CUDA runtime
# ============================================================
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3-pip python3.10-venv \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
        libgomp1 curl && \
    ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ──────────────────────────────────────
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Install PaddlePaddle GPU (CUDA 11.8 compatible)
# Falls back to CPU automatically if no GPU is detected at runtime
RUN pip install --no-cache-dir paddlepaddle-gpu==2.6.1.post118 \
        -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html || \
    pip install --no-cache-dir paddlepaddle==2.6.1

# Install PaddleOCR
RUN pip install --no-cache-dir "paddleocr>=2.7.0" "paddlex>=3.0.0"

# ── Local packages ───────────────────────────────────────────
COPY packages/ /app/packages/
RUN pip install --no-cache-dir \
        /app/packages/construction_ocr \
        /app/packages/construction_circle_detector \
        /app/packages/construction_llm_explainer \
        /app/packages/construction_plan_rag \
        /app/packages/construction_vlm_analyzer

# ── Pre-download heavy ML models ─────────────────────────────
# These are baked into the image so containers start instantly
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('[Docker] sentence-transformers model cached')"

RUN python -c "\
import os; os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK']='True'; \
from paddleocr import PaddleOCR; \
PaddleOCR(use_textline_orientation=True, lang='en', \
          ocr_version='PP-OCRv4', \
          use_doc_orientation_classify=False, \
          use_doc_unwarping=False); \
print('[Docker] PaddleOCR PP-OCRv4 models cached')"

# ── Copy backend code ────────────────────────────────────────
COPY backend/ /app/backend/

# ── Copy built frontend from Stage 1 ─────────────────────────
COPY --from=frontend-builder /build/app/dist/ /app/app/dist/

# ── Copy launcher (not used in Docker, but included) ─────────
COPY launcher.py /app/launcher.py

# ── Expose port ───────────────────────────────────────────────
EXPOSE 8001

# ── Health check ──────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/healthz || exit 1

# ── Startup ───────────────────────────────────────────────────
# Run uvicorn directly (bypass launcher.py which uses Tkinter GUI)
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
