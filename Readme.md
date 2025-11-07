# Generative AI for STEM Education

A comprehensive web application designed to enhance education through the power of Generative AI. This project combines Python FastAPI backend with Vite frontend to deliver an interactive and learning experience.


### Backend Setup

1. **Create and activate a Python virtual environment:**

   ```bash
   # Create virtual environment
   python3 -m venv .venv
   
   # Activate virtual environment
   # For macOS/Linux:
   source .venv/bin/activate
   
   # For Windows:
   .venv\Scripts\activate
   ```

2. **Install Python dependencies:**

   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Set up environment variables:**

   Create a `.env` file in the `backend/` directory and add your API keys:

   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Run the FastAPI backend:**

   ```bash
   cd backend
   python -m uvicorn app:app --reload --port 8001

   ```

   The backend will be available at `http://localhost:8001`

### Frontend Setup

1. **Navigate to the frontend directory:**

   ```bash
   cd app
   ```

2. **Install Node.js dependencies:**

   ```bash
   npm install
   ```

3. **Run the development server:**

   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173` 

