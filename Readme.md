# Gen_ai-for-stem-education

An AI-powered educational tool designed to assist students in understanding technical documents and construction drawings. It uses EasyOCR for text detection and an LLM (Groq) for generating context-aware explanations.

## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python**: Version 3.10 or higher (tested with 3.10).
    *   Check with: `python --version` or `python3 --version`
2.  **Node.js**: Version 18 or higher (for building the frontend).
    *   Check with: `node --version`
3.  **Git**: For cloning the repository.

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Gen_ai-for-stem-education
```

### 2. Backend Setup (Python)
It is recommended to use a virtual environment to manage dependencies.

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

**Mac / Linux (Terminal):**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

> **Note for Mac Users:** If you encounter issues installing `opencv-python` or `easyocr`, you may need to install system dependencies using Homebrew (e.g., `brew install opencv`).

### 3. Frontend Setup (React)
You need to build the frontend so the backend can serve it.

**Windows / Mac / Linux:**
```bash
cd app
npm install
npm run build
cd ..
```
This creates a `dist/` folder in `app/` which the backend serves as static files.

### 4. Environment Configuration
Create a `.env` file in the `backend/` directory (or check if one is provided securely). It should contain your API keys:

```ini
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CX=your_google_search_engine_id_here
```

## Running the Application

The easiest way to run the application is using the `launcher.py` script. This script checks for API keys, internet connection, and required packages, then starts the backend server and automatically opens the application in your default web browser.

**Ensure your virtual environment is activated first!**

**Windows (PowerShell):**
```powershell
python launcher.py
```

**Mac / Linux (Terminal):**
```bash
python3 launcher.py
```

*   The backend will start at `http://127.0.0.1:8001`.
*   The launcher will open this URL in your browser.

## Troubleshooting

### "No text detected"
*   Ensure `easyocr` is installed correctly.
*   The application uses GPU (CUDA) if available, otherwise it falls back to CPU. On some systems, the first run might be slow as it downloads OCR models.

### "Module not found"
*   Make sure you have activated your virtual environment (`.venv`) before running the launcher.

### "Missing API keys"
*   The launcher will explicitly tell you if `GROQ_API_KEY` or Google keys are missing. Check your `backend/.env` file.

### Mac-Specific Issues
*   If you see errors related to `libgl1` or OpenCV, install them via Homebrew: `brew install opencv`.
*   If using an M1/M2/M3 Mac, `easyocr` should work with CPU mode automatically, or Metal acceleration if configured in PyTorch (advanced).

## Project Structure
*   `launcher.py`: Main entry point.
*   `backend/`: Python FastAPI server, OCR logic, and API routes.
*   `app/`: React frontend source code.
*   `backend/sessions.db`: Local database for user sessions (auto-created).

