# ---------- Stage 1: build React (under app/) ----------
FROM node:20-alpine AS fe
WORKDIR /fe

# Copy manifests explicitly from app/
COPY app/package.json ./
COPY app/package-lock.json ./

# Debug: verify files arrived
RUN echo "LIST /fe after copying manifests:" && ls -la

# Use lockfile if present; otherwise fallback to npm install
RUN if [ -f package-lock.json ]; then npm ci --no-audit; else npm install; fi

# Copy the rest of the frontend source
COPY app/ .

# Build Vite app -> /fe/dist
RUN npm run build
RUN echo "LIST /fe/dist after build:" && ls -la /fe/dist

# ---------- Stage 2: FastAPI runtime ----------
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System libs for OpenCV/EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgl1 libglib2.0-0 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend code
COPY backend/ /app/backend/

# Copy built frontend into the folder FastAPI serves
COPY --from=fe /fe/dist/ /app/backend/frontend/

# Python deps (Torch CPU first)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
&& pip install --no-cache-dir -r backend/requirements.txt \
&& pip install --no-cache-dir uvicorn==0.30.1


# Hugging Face port + persistent DB path
ENV PORT=7860
ENV DB_PATH=/data/sessions.db

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
