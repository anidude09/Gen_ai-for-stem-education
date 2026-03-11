# Gen AI for STEM Education

An AI-powered tool that helps students learn from construction plan drawings. Upload a construction drawing, and the app will detect text, identify symbols, and explain what everything means using OpenAI's GPT-4o — all in a simple web interface.

## What It Does

1. **OCR Text Detection** — Uses PaddleOCR to find and read text labels on construction drawings
2. **Circle/Symbol Detection** — Identifies circled callouts and reference symbols using OpenCV
3. **AI Explanations** — Sends detected text to GPT-4o, which explains each term like a senior construction engineer would
4. **RAG Dictionary Lookup** — Matches terms against the RSMeans Illustrated Construction Dictionary for accurate definitions and images
5. **Visual Analysis (VLM)** — Uses GPT-4o Vision to analyze full drawings or selected regions and describe what's shown
6. **Activity Logging** — Tracks user interactions for research purposes

## Project Structure

```
Gen_ai-for-stem-education/
├── launcher.py                  # Main entry point — starts backend + opens browser
├── backend/                     # Python FastAPI server
│   ├── app.py                   # FastAPI app setup, routes, static file serving
│   ├── requirements.txt         # Python dependencies
│   ├── routes/
│   │   ├── detect.py            # OCR + circle detection endpoint
│   │   ├── llm.py               # LLM explanation endpoint
│   │   ├── llm_images.py        # LLM with image search endpoint
│   │   ├── vlm.py               # GPT-4o Vision analysis endpoint
│   │   ├── auth.py              # Login / session management
│   │   ├── regions_detect.py    # Region-specific detection
│   │   └── activity_log.py      # Activity logging endpoint
│   └── services/
│       ├── rag_service.py       # RAG dictionary lookup (uses construction_plan_rag)
│       └── google_images.py     # Google image search service
├── app/                         # React + Vite frontend
│   ├── package.json
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx              # Main application component
│       ├── main.jsx             # React entry point
│       ├── config.js            # API base URL config
│       ├── components/
│       │   ├── ImageCanvas.jsx  # Canvas for drawing interaction
│       │   ├── ImageUploader.jsx
│       │   ├── Loginform.jsx
│       │   ├── Page.jsx         # Page navigation component
│       │   ├── Popup.jsx        # Term explanation popup
│       │   ├── ShapeOverlay.jsx # Detected shape rendering
│       │   ├── VLMPanel.jsx     # Vision analysis panel
│       │   └── ZoomControls.jsx
│       ├── hooks/               # Custom React hooks
│       ├── styles/              # CSS stylesheets
│       └── utils/
│           └── activityLogger.js
├── packages/                    # Reusable Python packages
│   ├── construction_ocr/        # PaddleOCR text detection pipeline
│   ├── construction_circle_detector/  # OpenCV circle detection
│   ├── construction_llm_explainer/    # Groq LLM explanation logic
│   ├── construction_plan_rag/         # RAG + dictionary term lookup
│   └── construction_vlm_analyzer/     # GPT-4o Vision analysis
├── data/                        # Reference data (not in repo, see below)
│   ├── Construction-Vocabulary.pdf
│   ├── RSMeans Illustrated Construction Dictionary.pdf
│   └── RSMeans_Illustrated_Construction_Dictionary/
│       ├── terms.json           # Extracted dictionary terms
│       └── images/              # Extracted page images
└── docs/                        # Local documentation (not in repo)
    ├── system-diagram.mmd       # Mermaid architecture diagram
    └── system_prompts.txt       # LLM system prompts reference
```

> **Note:** The `data/` and `docs/` folders are not included in the GitHub repo. See the [Data Setup](#4-data-setup) section below for how to set them up.

## Prerequisites

Make sure you have these installed:

- **Python 3.10+** — Check with `python --version`
- **Node.js 18+** — Check with `node --version`
- **Git** — For cloning the repository

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Gen_ai-for-stem-education.git
cd Gen_ai-for-stem-education
```

### 2. Set Up the Python Backend

Create a virtual environment and install dependencies.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

The backend also depends on the local packages in `packages/`. Install them in editable mode:

```bash
pip install -e packages/construction_ocr
pip install -e packages/construction_circle_detector
pip install -e packages/construction_llm_explainer
pip install -e packages/construction_plan_rag
pip install -e packages/construction_vlm_analyzer
```

> **Mac users:** If you run into issues with `opencv-python`, try `brew install opencv` first.

### 3. Set Up the React Frontend

```bash
cd app
npm ci
npm run build
cd ..
```

This creates a `dist/` folder inside `app/` that the backend serves automatically.

> If `npm ci` doesn't work, try deleting `node_modules/` and running `npm install` followed by `npm run build`.

### 4. Data Setup

The `data/` folder is not included in the repo because the files are large. To set it up:

1. Create a `data/` folder in the project root
2. Place the following files in it:
   - `Construction-Vocabulary.pdf`
   - `RSMeans Illustrated Construction Dictionary.pdf`
3. Create `data/RSMeans_Illustrated_Construction_Dictionary/` and add:
   - `terms.json` — Extracted dictionary terms (JSON)
   - `images/` — Extracted page images organized by page number

> Ask a team member for these files or generate them from the source PDFs.

### 5. API Keys

Create a `.env` file in the `backend/` folder with your API keys:

```ini
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_CSE_API_KEY=your_google_custom_search_api_key_here
GOOGLE_CSE_CX=your_google_custom_search_engine_id_here
```

You'll need:
- An **OpenAI API key** from [platform.openai.com](https://platform.openai.com) — used for GPT-4o text explanations and Vision analysis
- A **Google Custom Search API key + Search Engine ID** from [Google Cloud Console](https://console.cloud.google.com) — used for image search

Optionally, you can also add a Groq key as a fallback for text explanations:
```ini
GROQ_API_KEY=your_groq_api_key_here
```

> Do **not** commit the `.env` file to Git.

## Running the App

Make sure your virtual environment is activated, then:

**Windows:**
```powershell
python launcher.py
```

**Mac / Linux:**
```bash
python3 launcher.py
```

The launcher will:
1. Check that all dependencies and API keys are set up
2. Start the backend server at `http://127.0.0.1:8001`
3. Open the app in your default browser

## How It Works

When you upload a construction drawing:

1. The **frontend** sends the image to the backend
2. **PaddleOCR** detects all readable text on the drawing
3. **OpenCV** finds circled callout symbols
4. Detected items are shown as clickable overlays on the image
5. Clicking a text label sends it to **GPT-4o**, which explains the term using construction domain knowledge
6. The **RAG service** searches the RSMeans construction dictionary for matching terms and images
7. You can also select a region and run **GPT-4o Vision analysis** for a detailed breakdown of that area

## Troubleshooting

| Problem | Solution |
|---|---|
| "No text detected" | Make sure PaddleOCR is installed properly. First run may be slow (downloading models). |
| "Module not found" | Activate your virtual environment first. Make sure packages are installed with `pip install -e`. |
| "Missing API keys" | Check your `backend/.env` file has all three keys. |
| OpenCV errors on Mac | Run `brew install opencv`. |
| Slow on M1/M2/M3 Mac | PaddleOCR uses CPU mode by default. This is normal. |
