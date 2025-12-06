import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse, FileResponse

from routes import detect, llm, auth, regions_detect, llm_images, activity_log

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
app.include_router(llm_images.router, prefix="/llm-images", tags=["LLM Images"])
app.include_router(activity_log.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Serve built frontend if available
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIST_DIR = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "app", "dist"))

if os.path.isdir(_FRONTEND_DIST_DIR):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_FRONTEND_DIST_DIR, "assets")),
        name="assets",
    )
    images_dist = os.path.join(_FRONTEND_DIST_DIR, "images")
    if os.path.isdir(images_dist):
        app.mount("/images", StaticFiles(directory=images_dist), name="images")


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = os.path.join(_FRONTEND_DIST_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Backend is running !"})
