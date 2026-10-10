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

# Global model inference lock (one heavy inference job at a time on free CPU)
model_lock = asyncio.Lock()

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

    # Clean timestamps older than 60s
    timestamps = [ts for ts in ip_request_timestamps[client_ip] if ts > cutoff]
    timestamps.append(now)
    ip_request_timestamps[client_ip] = timestamps

    if len(timestamps) > RATE_LIMIT_PER_MIN:
        logger.warning("Rate limit exceeded for IP %s (%d requests in last 60s)", client_ip, len(timestamps))
        raise HTTPException(
            status_code=429,
            detail="Slow down a little, then try again."
        )


@asynccontextmanager
async def acquire_model_slot():
    """Ensures only one model job runs at a time. Returns 503 if busy."""
    is_locked = model_lock.locked()
    logger.info("[Lock Check] Checking model lock. Currently locked: %s", is_locked)
    if is_locked:
        logger.warning("[Lock Rejection] Model lock is busy! Rejecting request with HTTP 503.")
        raise HTTPException(
            status_code=503,
            detail="The server is busy. Try again in a moment."
        )
    logger.info("[Lock Acquire] Acquiring model lock...")
    async with model_lock:
        logger.info("[Lock Acquired] Model lock acquired successfully.")
        try:
            yield
        finally:
            logger.info("[Lock Released] Model lock released.")


async def validate_and_load_image(file: UploadFile) -> Image.Image:
    """
    Validates file size (max 8MB), ensures valid image format,
    applies ImageOps.exif_transpose for phone camera orientation,
    and returns a Pillow Image.
    """
    logger.info("[Image Load] Reading uploaded file '%s' (content-type: %s)...", file.filename, file.content_type)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        logger.warning("[Image Load Failed] File exceeds %d bytes (got %d bytes)", MAX_UPLOAD_BYTES, len(content))
        raise HTTPException(
            status_code=400,
            detail="Image is too large. Maximum size is 8MB."
        )

    if not content:
        logger.warning("[Image Load Failed] Uploaded file is empty.")
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    logger.info("[Image Load] Read %d bytes. Verifying format with Pillow...", len(content))
    try:
        image = Image.open(io.BytesIO(content))
        # Correct mobile phone EXIF orientation before any processing
        image = ImageOps.exif_transpose(image)
        image.load()
        if image.format not in ("JPEG", "PNG", "WEBP"):
            image = image.convert("RGB")
        logger.info("[Image Load Success] Image verified: size=%s, format=%s, mode=%s", image.size, image.format, image.mode)
        return image
    except Exception as exc:
        logger.error("[Image Load Failed] Pillow validation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image (JPEG, PNG, or WEBP)."
        )
