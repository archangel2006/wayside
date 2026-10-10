import asyncio
import logging
import os
import time
from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.limits import check_rate_limit, acquire_model_slot, validate_and_load_image
from app.services.cutout import remove_background

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("wayside.main")

app = FastAPI(
    title="Wayside",
    description="Stateless backend for Wayside specimen collector",
    version="1.0.0"
)

# Friendly JSON errors, never leak stack traces to client, but log full trace to console
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("[Server Error 500] Unhandled exception occurred during request %s %s:", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on the server."}
    )

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/cutout")
async def cutout_endpoint(request: Request, file: UploadFile = File(...)):
    t0 = time.time()
    logger.info("[Request Start] POST /api/cutout received from %s", request.client.host if request.client else "unknown")
    
    check_rate_limit(request)
    
    async with acquire_model_slot():
        image = await validate_and_load_image(file)
        logger.info("[Cutout Dispatch] Running remove_background in background thread...")
        png_bytes = await asyncio.to_thread(remove_background, image)
        total_time = time.time() - t0
        logger.info("[Request Complete] POST /api/cutout finished successfully in %.2fs, returning %d bytes PNG", total_time, len(png_bytes))
        return Response(content=png_bytes, media_type="image/png")

# Mount static folder
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
