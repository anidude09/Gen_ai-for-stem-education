from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

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


@app.get("/", tags=["Root"])
def read_root():
    return JSONResponse({"message": "Backend is running !"})
