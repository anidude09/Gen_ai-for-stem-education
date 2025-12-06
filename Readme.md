# Gen_ai-for-stem-education

An AI-powered educational tool designed to assist students in understanding technical documents and construction drawings. It uses EasyOCR for text detection and an LLM (Groq) for generating context-aware explanations.

## Prerequisites

Before you begin, ensure you have the following installed on **each machine** (Windows or Mac):

1.  **Python**: Version 3.10 or higher (tested with 3.10).  
    - Check with: `python --version` or `python3 --version`
2.  **Node.js + npm**: Version 18 or higher (for building the frontend).  
    - Check with: `node --version`
3.  **Git**: For cloning the repository.

> You do **not** need to copy a `.venv` or `node_modules` folder between machines.  
> Each machine should create its own Python virtual environment and install packages from the shared config files.

## Installation & Setup

### 1. Clone the Repository (Windows + Mac)

```bash
git clone <repository-url>
cd Gen_ai-for-stem-education
```

### 2. Backend Setup (Python, using `backend/requirements.txt`)

Create an isolated Python environment per machine and install the backend dependencies.

**Windows (PowerShell):**

```powershell
# From the project root
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip (recommended)
python -m pip install --upgrade pip

# Install backend dependencies
pip install -r backend/requirements.txt
```

**Mac / Linux (Terminal):**

```bash
# From the project root
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip (recommended)
python -m pip install --upgrade pip

# Install backend dependencies
pip install -r backend/requirements.txt
```

> **Note for Mac Users:**  
> If you encounter issues installing `opencv-python` or `easyocr`, you may need to install system dependencies using Homebrew, for example:  
> `brew install opencv`

### 3. Frontend Setup (React, using `package-lock.json`)

The frontend dependencies are pinned via `package-lock.json`. On a **fresh clone**, prefer `npm ci` to exactly reproduce the versions:

**Windows / Mac / Linux:**

```bash
cd app

# Install exact dependencies defined in package-lock.json
npm ci

# Build the production bundle that the backend will serve
npm run build

cd ..
```

This creates a `dist/` folder in `app/` which the backend serves as static files.

> If `npm ci` fails because `node_modules` already exists or for other local reasons, you can delete `node_modules` and retry, or fall back to:
> ```bash
> npm install
> npm run build
> ```

### 4. Environment Configuration (API Keys)

On each machine, create a `.env` file in the `backend/` directory (or in the project root; the launcher checks both). It should contain your API keys:

```ini
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_CSE_API_KEY=your_google_custom_search_api_key_here
GOOGLE_CSE_CX=your_google_custom_search_engine_id_here
```

These keys are used by:
- `backend/routes/llm.py` and `backend/routes/llm_images.py` (Groq LLM)
- `backend/services/google_images.py` (Google Programmable Search for images)

Do **not** commit your `.env` file to Git; keep it local or share via a secure channel.
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
*   The launcher will explicitly tell you if `GROQ_API_KEY`, `GOOGLE_CSE_API_KEY`, or `GOOGLE_CSE_CX` are missing. Check your `.env` file in the project root or `backend/`.

### Mac-Specific Issues
*   If you see errors related to `libgl1` or OpenCV, install them via Homebrew: `brew install opencv`.
*   If using an M1/M2/M3 Mac, `easyocr` should work with CPU mode automatically, or Metal acceleration if configured in PyTorch (advanced).

## Project Structure
*   `launcher.py`: Main entry point.
*   `backend/`: Python FastAPI server, OCR logic, and API routes.
*   `app/`: React frontend source code.
*   `backend/sessions.db`: Local database for user sessions (auto-created).

