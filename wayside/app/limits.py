import asyncio
import io
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import HTTPException, Request, UploadFile
from PIL import Image, ImageOps

from app.config import MAX_UPLOAD_BYTES, RATE_LIMIT_PER_MIN

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
        raise HTTPException(
            status_code=429,
            detail="Slow down a little, then try again."
        )


@asynccontextmanager
async def acquire_model_slot():
    """Ensures only one model job runs at a time. Returns 503 if busy."""
    if model_lock.locked():
        raise HTTPException(
            status_code=503,
            detail="The server is busy. Try again in a moment."
        )
    async with model_lock:
        yield


async def validate_and_load_image(file: UploadFile) -> Image.Image:
    """
    Validates file size (max 8MB), ensures valid image format,
    applies ImageOps.exif_transpose for phone camera orientation,
    and returns a Pillow Image.
    """
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Image is too large. Maximum size is 8MB."
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    try:
        image = Image.open(io.BytesIO(content))
        # Correct mobile phone EXIF orientation before any processing
        image = ImageOps.exif_transpose(image)
        image.load()
        if image.format not in ("JPEG", "PNG", "WEBP"):
            image = image.convert("RGB")
        return image
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image (JPEG, PNG, or WEBP)."
        )
