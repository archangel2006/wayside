import asyncio
import os
from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.limits import check_rate_limit, acquire_model_slot, validate_and_load_image
from app.services.cutout import remove_background

app = FastAPI(
    title="Wayside",
    description="Stateless backend for Wayside specimen collector",
    version="1.0.0"
)

# Friendly JSON errors, never leak stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on the server."}
    )

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/cutout")
async def cutout_endpoint(request: Request, file: UploadFile = File(...)):
    check_rate_limit(request)
    async with acquire_model_slot():
        image = await validate_and_load_image(file)
        png_bytes = await asyncio.to_thread(remove_background, image)
        return Response(content=png_bytes, media_type="image/png")

# Mount static folder
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
