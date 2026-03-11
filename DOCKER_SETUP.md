# Docker Setup Guide — Gen AI for STEM Education

## Prerequisites

1. **Docker Desktop** — [Install here](https://docs.docker.com/desktop/install/windows-install/)
2. **NVIDIA Container Toolkit** (for GPU support) — [Install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
3. **Your `data/` folder** — Must be in the project root (contains PDFs, terms.json, dictionary images)
4. **API keys** — OpenAI, Google CSE

---

## Quick Start (5 steps)

### 1. Clone the repo
```bash
git clone https://github.com/anidude09/Gen_ai-for-stem-education.git
cd Gen_ai-for-stem-education
```

### 2. Add the `data/` folder
Place your `data/` folder in the project root. It should contain:
```
data/
├── terms.json
├── *.pdf files (construction documents)
└── RSMeans_Illustrated_Construction_Dictionary/
    └── images/
```

### 3. Create your `.env` file
```bash
cp .env.example .env
```
Edit `.env` and fill in your API keys:
```env
OPENAI_API_KEY=sk-your-actual-key-here
GOOGLE_CSE_API_KEY=your-key-here
GOOGLE_CSE_CX=your-cx-here
GROQ_API_KEY=your-key-here          # optional fallback
```

### 4. Build the Docker image
```bash
docker compose build
```
> **First build takes 10-15 minutes** — it downloads CUDA, Python packages, PaddleOCR models, and sentence-transformer models. Subsequent builds are cached and fast.

### 5. Run the container
```bash
docker compose up
```
Open **http://localhost:8001** in your browser.

---

## What Happens Under the Hood

```
┌─────────────────────────────────────────────────────┐
│  Docker Image (~6 GB)                               │
│                                                     │
│  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │ Built React  │  │ Python 3.10 + CUDA 11.8      │ │
│  │ Frontend     │  │ FastAPI + uvicorn            │ │
│  │ (static)     │  │ PaddleOCR (GPU models cached)│ │
│  └──────────────┘  │ sentence-transformers cached │ │
│                    │ 5 local packages installed   │ │
│                    └──────────────────────────────┘ │
└─────────┬───────────────────────────────┬───────────┘
          │                               │
    ┌─────▼─────┐                  ┌──────▼──────┐
    │ data/     │ (volume mount)   │ chroma_db/  │ (named volume)
    │ PDFs,     │                  │ Vector DB   │
    │ terms,    │                  │ persisted   │
    │ images    │                  │ across      │
    └───────────┘                  │ restarts    │
                                   └─────────────┘
```

**Build stages:**
1. **Stage 1 (Node.js):** Installs npm packages, builds React frontend → static files
2. **Stage 2 (CUDA + Python):** Installs backend deps, PaddlePaddle GPU, 5 local packages, pre-downloads ML models, copies built frontend

---

## GPU vs CPU

### With GPU (default)
The `docker-compose.yml` includes GPU reservation. Requires:
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed
- Docker Desktop with WSL2 backend (Windows)

### Without GPU (CPU only)
Remove the `deploy` section from `docker-compose.yml`:
```yaml
services:
  stem-ai:
    build: .
    container_name: stem-ai-app
    ports:
      - "8001:8001"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - chroma_db:/app/backend/chroma_db
    restart: unless-stopped
    # deploy section removed — runs on CPU

volumes:
  chroma_db:
    driver: local
```

PaddleOCR will automatically use CPU if no GPU is available at runtime.

---

## Common Commands

| Action | Command |
|---|---|
| Build image | `docker compose build` |
| Start container | `docker compose up` |
| Start (background) | `docker compose up -d` |
| View logs | `docker compose logs -f` |
| Stop container | `docker compose down` |
| Rebuild after code changes | `docker compose build --no-cache` |
| Shell into container | `docker compose exec stem-ai bash` |
| Check GPU inside container | `docker compose exec stem-ai python -c "import paddle; print(paddle.device.get_device())"` |

---

## Data Volume

The `data/` folder is **not baked into the image** — it's mounted at runtime via Docker volumes. This means:
- You can update PDFs without rebuilding the image
- First run will build the ChromaDB vector store from your PDFs (~3-10 min)
- Subsequent runs load the cached vector store instantly (persisted in the `chroma_db` named volume)

To **rebuild the vector store** (e.g., after adding new PDFs):
```bash
docker compose down -v    # -v removes named volumes
docker compose up         # rebuilds chroma_db from scratch
```

---

## Sharing with Others

### Option A: Export the image
```bash
docker save stem-ai-app | gzip > stem-ai-app.tar.gz
# Give them this file + data/ folder + .env.example
```

They load it:
```bash
docker load < stem-ai-app.tar.gz
# Place data/ folder, create .env, then:
docker compose up
```

### Option B: Push to Docker Hub
```bash
docker tag stem-ai-app yourusername/stem-ai-app:latest
docker push yourusername/stem-ai-app:latest
```

---

## Troubleshooting

**"No NVIDIA GPU detected"** — The app still works on CPU. PaddleOCR auto-falls back.

**"OPENAI_API_KEY not set"** — Make sure your `.env` file exists and has valid keys.

**"chroma_db taking long to build"** — Normal on first run (7500+ chunks). Wait ~5 min.

**Build fails at PaddlePaddle** — If you don't have a compatible GPU, the Dockerfile tries to fall back to CPU PaddlePaddle automatically.

**Port 8001 already in use** — Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "9000:8001"    # access at http://localhost:9000
```
