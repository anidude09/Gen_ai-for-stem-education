from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, FileResponse

from fastapi.staticfiles import StaticFiles

import os
from pathlib import Path

from backend.routes import detect, llm,auth, regions_detect

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect.router, prefix="/detect", tags=["Detection"])
app.include_router(llm.router, prefix="/llm", tags=["LLM"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(regions_detect.router, prefix="/detect", tags=["Region Detection"])



@app.get("/healthz")
def health():
    return {"ok": True}



# @app.get("/", tags=["Root"])
# def read_root():
#     return JSONResponse({"message": "Backend is running!"})


HERE = Path(__file__).resolve().parent
FE_DIR = HERE / "frontend"

app.mount("/assets", StaticFiles(directory=str(FE_DIR / "assets")), name="assets")
app.mount("/images", StaticFiles(directory=str(FE_DIR / "images")), name="images")

@app.get("/")
def index():
    return FileResponse(FE_DIR / "index.html")

@app.get("/favicon.co")
def favicon():
    return JSONResponse({"detail": "No favicon configured"}, status_code=404)


# FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
# if os.path.isdir(FRONTEND_DIR):
#     app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

