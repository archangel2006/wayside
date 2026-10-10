"""
app/main.py
FastAPI application: routes, startup, static serving.

Routes:
  GET  /api/health     — liveness check
  POST /api/cutout     — background removal (rembg u2netp)
  POST /api/label      — find naming (SmolVLM-256M or configured model)
  POST /api/story      — story generation (Qwen2.5-0.5B or configured model)
  GET  /               — serves static/ frontend

Design notes:
  - Each model route uses its own asyncio.Lock, so /api/cutout and /api/label
    can run truly in parallel when the browser sends Promise.all (every snap).
  - All model inference runs in asyncio.to_thread() so it never blocks the event loop.
  - Lazy model loading: nothing heavy is imported at startup; server binds port instantly.
  - No uploads, images, or story text are stored anywhere on the server.
"""
import asyncio
import logging
import os
import time
from typing import List, Optional

from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.limits import (
    acquire_lock,
    check_rate_limit,
    cutout_lock,
    story_lock,
    validate_and_load_image,
    vision_lock,
)
from app.services.cutout import remove_background
from app.services.vision import label_image
from app.services.story import generate_story

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("wayside.main")


app = FastAPI(
    title="Wayside",
    description="Stateless backend: background removal, find labeling, story generation.",
    version="1.0.0",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("[500] Unhandled error on %s %s:", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server."})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/cutout
# Input:  multipart file upload (image)
# Output: image/png (transparent background removed)
# ---------------------------------------------------------------------------

@app.post("/api/cutout")
async def cutout_endpoint(request: Request, file: UploadFile = File(...)):
    from app.config import MODEL_TIMEOUT_SEC
    t0 = time.time()
    check_rate_limit(request)
    async with acquire_lock(cutout_lock, "cutout"):
        image = await validate_and_load_image(file)
        png_bytes = await asyncio.wait_for(
            asyncio.to_thread(remove_background, image),
            timeout=float(MODEL_TIMEOUT_SEC)
        )
        logger.info("[cutout] done in %.2fs, %d bytes", time.time() - t0, len(png_bytes))
        return Response(content=png_bytes, media_type="image/png")


# ---------------------------------------------------------------------------
# POST /api/label
# Input:  multipart file upload (image)
# Output: {"label": str, "description": str}
# ---------------------------------------------------------------------------

@app.post("/api/label")
async def label_endpoint(request: Request, file: UploadFile = File(...)):
    from app.config import MODEL_TIMEOUT_SEC
    t0 = time.time()
    check_rate_limit(request)
    async with acquire_lock(vision_lock, "vision"):
        image = await validate_and_load_image(file)
        result = await asyncio.wait_for(
            asyncio.to_thread(label_image, image),
            timeout=float(MODEL_TIMEOUT_SEC)
        )
        logger.info("[label] done in %.2fs: %s", time.time() - t0, result)
        return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# POST /api/story
# Input:  {"items": [...], "theme": str, "place": str}
# Output: {"title": str, "text": str}
# ---------------------------------------------------------------------------

class StoryItem(BaseModel):
    label: str
    description: str = ""
    note: str = ""

class StoryRequest(BaseModel):
    items: List[StoryItem]
    theme: Optional[str] = "quiet"
    place: Optional[str] = ""

@app.post("/api/story")
async def story_endpoint(request: Request, body: StoryRequest):
    from app.config import MODEL_TIMEOUT_SEC
    t0 = time.time()
    check_rate_limit(request)

    # Cap inputs for safety
    items = [i.model_dump() for i in body.items[:8]]
    theme = (body.theme or "quiet").strip()[:40]
    place = (body.place or "").strip()[:60]

    async with acquire_lock(story_lock, "story"):
        result = await asyncio.wait_for(
            asyncio.to_thread(generate_story, items, theme, place),
            timeout=float(MODEL_TIMEOUT_SEC)
        )
        logger.info("[story] done in %.2fs", time.time() - t0)
        return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
