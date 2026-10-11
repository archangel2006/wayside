"""
app/limits.py
Public-server safety: upload validation, per-IP rate limiting, per-model concurrency lock.

Key design decisions:
- Each model type has its own asyncio.Lock so that /api/cutout and /api/label
  can run truly concurrently when the browser sends them in parallel (Promise.all).
  A single global lock would serialize them and double latency for every snap.
- HTTPExceptions raised here propagate cleanly to FastAPI's exception handler.
- EXIF transpose is applied before any model sees the image.
- Rate limit uses X-Forwarded-For (Render's reverse proxy sets this).
"""
import asyncio
import io
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import HTTPException, Request, UploadFile
from PIL import Image, ImageOps

from app.config import MAX_UPLOAD_BYTES, RATE_LIMIT_PER_MIN

logger = logging.getLogger("wayside.limits")

# Separate locks per model type so /api/cutout + /api/label can run in parallel
cutout_lock = asyncio.Lock()
vision_lock = asyncio.Lock()
story_lock = asyncio.Lock()
cover_lock = asyncio.Lock()

# Simple sliding window rate limiter by client IP
ip_request_timestamps: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(request: Request):
    """Enforces simple per-IP rate limit using X-Forwarded-For when available. Returns 429 when exceeded."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    now = time.time()
    cutoff = now - 60.0

    timestamps = [ts for ts in ip_request_timestamps[client_ip] if ts > cutoff]
    timestamps.append(now)
    ip_request_timestamps[client_ip] = timestamps

    if len(timestamps) > RATE_LIMIT_PER_MIN:
        logger.warning("Rate limit exceeded for IP %s (%d req/60s)", client_ip, len(timestamps))
        raise HTTPException(status_code=429, detail="Slow down a little, then try again.")


@asynccontextmanager
async def acquire_lock(lock: asyncio.Lock, name: str, timeout: float = 15.0):
    """
    Acquire a named model lock. Waits up to `timeout` seconds before rejecting with HTTP 503.
    This prevents instant 503s when brief concurrent requests arrive.
    """
    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("[Lock Rejection] %s lock busy after %.1fs timeout", name, timeout)
        raise HTTPException(status_code=503, detail="The server is busy. Try again in a moment.")
    
    logger.info("[Lock] %s acquired", name)
    try:
        yield
    finally:
        lock.release()
        logger.info("[Lock] %s released", name)


async def validate_and_load_image(file: UploadFile) -> Image.Image:
    """
    Validates file size (max 8MB), verifies it is a real image with Pillow,
    applies EXIF orientation correction, downscales raw camera photos > 1200px to save RAM,
    and returns a Pillow Image.
    """
    logger.info("[Image Load] Reading '%s' (content-type: %s)...", file.filename, file.content_type)
    content = await file.read(MAX_UPLOAD_BYTES + 1)

    if len(content) > MAX_UPLOAD_BYTES:
        logger.warning("[Image Load Failed] %d bytes > %d byte limit", len(content), MAX_UPLOAD_BYTES)
        raise HTTPException(status_code=400, detail="Image is too large. Maximum size is 8MB.")

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        # Guard against raw phone camera 12-48MP images exhausting memory
        max_dim = max(image.size)
        if max_dim > 1200:
            scale = 1200.0 / max_dim
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.BILINEAR
            )
            logger.info("[Image Load Rescaled] Downscaled camera photo from %dpx to %s", max_dim, image.size)

        logger.info("[Image Load OK] size=%s, mode=%s", image.size, image.mode)
        return image
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Image Load Failed] Pillow error: %s", exc)
        raise HTTPException(status_code=400, detail="Please upload a valid image (JPEG, PNG, or WEBP).")
