"""
app/services/providers.py
External inference provider abstraction for vision labeling and story generation.

Supports:
- "hf" / "huggingface": HF free Serverless Inference API (no credits needed)
  - Vision: Salesforce/blip-image-captioning-base  (image-to-text pipeline)
  - Story:  Falconsai/text_summarization via text-generation pipeline
- "hf-router": HF Router (paid, credits required) — kept for completeness
- "fallback": Instant offline heuristic fallback (always works, no network)

Maintains identical response contracts:
- Vision: {"label": str, "description": str}
- Story:  {"title": str, "text": str}

Free-tier HF models used:
  Vision:  Salesforce/blip-image-captioning-base
           nlpconnect/vit-gpt2-image-captioning  (backup)
  Story:   mistralai/Mixtral-8x7B-Instruct-v0.1 — no credits via pipeline API
           Use: text-generation endpoint, max_new_tokens=220
           (HF free API allows 30s bursts on any public model)
"""
import base64
import io
import json
import logging
import re
import time
from typing import Optional

import httpx
from PIL import Image

from app.config import (
    HF_TOKEN,
    HF_API_BASE,
    HF_ROUTER_BASE,
    WAYSIDE_VISION_MODEL,
    WAYSIDE_STORY_MODEL,
    MODEL_TIMEOUT_SEC,
)

logger = logging.getLogger("wayside.providers")

# --------------------------------------------------------------------------
# Free HF Serverless — image-to-text models (no credits needed)
# These are classic pipeline endpoints, not the router.
# --------------------------------------------------------------------------
FREE_VISION_MODELS = [
    "Salesforce/blip-image-captioning-base",
    "nlpconnect/vit-gpt2-image-captioning",
]

# Free HF text-generation models (used for story, classic pipeline)
FREE_STORY_MODELS = [
    "tiiuae/falcon-7b-instruct",
    "bigscience/bloom-560m",
]

LABEL_PROMPT = (
    "You are labeling an object a person found on a walk. "
    "Reply with JSON only, no other text, in this exact shape: "
    '{"label": "<2 to 4 words>", "description": "<one short, playful phrase, under 8 words>"} '
    "Name the main object only. If you are unsure, give your best short guess."
)


# --------------------------------------------------------------------------
# Image helpers
# --------------------------------------------------------------------------

def pil_to_base64_jpeg(image: Image.Image, max_dim: int = 512) -> str:
    """Resize image defensively and encode as base64 JPEG."""
    if max(image.size) > max_dim:
        scale = max_dim / max(image.size)
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.Resampling.LANCZOS
        )
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def pil_to_jpeg_bytes(image: Image.Image, max_dim: int = 512) -> bytes:
    """Resize and return raw JPEG bytes (for pipeline API)."""
    if max(image.size) > max_dim:
        scale = max_dim / max(image.size)
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.Resampling.LANCZOS
        )
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# --------------------------------------------------------------------------
# JSON parsers
# --------------------------------------------------------------------------

def parse_label_json(text: str) -> Optional[dict]:
    """Defensively extract label JSON from raw model output."""
    if not text:
        return None
    cleaned = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "").strip()
    m = re.search(r"\{[^{}]+\}", cleaned, re.DOTALL)
    if not m:
        return None
    for candidate in [m.group(0), m.group(0).replace("'", '"')]:
        try:
            obj = json.loads(candidate)
            label = str(obj.get("label", "")).strip()[:60]
            description = str(obj.get("description", "")).strip()[:80]
            if label and description and "<" not in label and ">" not in label:
                return {"label": label, "description": description}
        except (json.JSONDecodeError, AttributeError):
            pass
    return None


import re as _re

def _clean_llm_text(s: str) -> str:
    """Strip markdown and plain-text formatting artifacts that LLMs emit."""
    # Remove horizontal rules
    s = _re.sub(r'^[-*_]{3,}\s*$', '', s, flags=_re.MULTILINE)
    # Remove bold/markdown label lines: **Title:** / **Line 1:** / **Paragraph:**
    s = _re.sub(r'^\*{1,2}(Title|Paragraph|Line|Part|Section|Chapter)\s*\d*\*{0,2}:?\*{0,2}\s*$', '', s, flags=_re.MULTILINE | _re.IGNORECASE)
    # Strip bold/italic markers: **text** -> text, *text* -> text
    s = _re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', s)
    # Strip markdown heading markers at line start (# ## ###)
    s = _re.sub(r'^#{1,6}\s+', '', s, flags=_re.MULTILINE)
    # Strip "Title: " / "Title:" prefix if it appears at start
    s = _re.sub(r'^title:\s*', '', s, flags=_re.IGNORECASE)
    # Strip plain-text section header lines: standalone short lines ending with ":"
    # e.g. "Opening Scene:", "Discoveries:", "Findings & Observations:", "Sequence:"
    s = _re.sub(r'^[A-Z][A-Za-z ,&\-]{1,50}:\s*$', '', s, flags=_re.MULTILINE)
    # Collapse excess blank lines to single blank line
    s = _re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def parse_story_text(raw: str, fallback_title: str) -> Optional[dict]:
    """Parse raw LLM output into title and story text, stripping markdown artifacts."""
    if not raw:
        return None

    cleaned = _clean_llm_text(raw)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]

    if len(lines) >= 2:
        title = lines[0].strip("#").strip()
        text = "\n".join(lines[1:]).strip()
    elif len(lines) == 1:
        title = fallback_title
        text = lines[0]
    else:
        return None

    # Sanity: if title is too long it leaked story text
    if len(title) > 120:
        title = fallback_title

    text = _clean_llm_text(text)
    return {"title": title, "text": text}


# --------------------------------------------------------------------------
# Free HF Serverless — image-to-text pipeline (no credits, rate limited ~10/min)
# --------------------------------------------------------------------------

def call_hf_free_vision(image: Image.Image) -> Optional[dict]:
    """
    Use the free HF Inference API (image-to-text pipeline).
    Returns a generated caption, then converts it to label/description format.
    No credits needed — uses token for higher rate limit only.
    """
    img_bytes = pil_to_jpeg_bytes(image, max_dim=448)
    headers = {"Content-Type": "image/jpeg"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    for model in FREE_VISION_MODELS:
        url = f"{HF_API_BASE.rstrip('/')}/{model}"
        try:
            resp = httpx.post(url, headers=headers, content=img_bytes, timeout=float(MODEL_TIMEOUT_SEC))
            logger.info("[HF Free Vision] %s -> HTTP %s", model, resp.status_code)
            if resp.status_code == 503:
                # Model is loading — retry once after brief wait
                logger.info("[HF Free Vision] Model loading, waiting 5s...")
                time.sleep(5)
                resp = httpx.post(url, headers=headers, content=img_bytes, timeout=float(MODEL_TIMEOUT_SEC))
            if resp.status_code == 200:
                data = resp.json()
                # Response format: [{"generated_text": "a green feather on the ground"}]
                if isinstance(data, list) and data:
                    caption = str(data[0].get("generated_text", "")).strip()
                elif isinstance(data, dict):
                    caption = str(data.get("generated_text", "")).strip()
                else:
                    caption = ""

                if caption:
                    logger.info("[HF Free Vision] Caption: %r", caption[:100])
                    # Convert caption to label/description
                    label = _caption_to_label(caption)
                    desc = caption[:60].rstrip(".")
                    return {"label": label, "description": desc}
            else:
                logger.warning("[HF Free Vision] HTTP %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.error("[HF Free Vision Error] %s: %s", model, exc)

    return None


def _caption_to_label(caption: str) -> str:
    """Extract a 2-4 word label from an image caption."""
    # Strip common prefixes from captioning models
    for prefix in ("a photo of ", "a ", "an ", "the ", "photo of a ", "image of a "):
        if caption.lower().startswith(prefix):
            caption = caption[len(prefix):]
            break
    # Take first 4 words only
    words = caption.strip().rstrip(".").split()[:4]
    return " ".join(words).title() if words else "Mystery find"


# --------------------------------------------------------------------------
# Free HF Serverless — text-generation pipeline (story, no credits)
# --------------------------------------------------------------------------

def call_hf_free_story(prompt: str) -> Optional[str]:
    """
    Use the free HF Inference API (text-generation pipeline) for story generation.
    Rate-limited but free. Uses the simplest possible public models.
    """
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    for model in FREE_STORY_MODELS:
        url = f"{HF_API_BASE.rstrip('/')}/{model}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 220,
                "temperature": 0.7,
                "return_full_text": False,
                "do_sample": True,
            }
        }
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=float(MODEL_TIMEOUT_SEC))
            logger.info("[HF Free Story] %s -> HTTP %s", model, resp.status_code)
            if resp.status_code == 503:
                logger.info("[HF Free Story] Model loading, waiting 5s...")
                time.sleep(5)
                resp = httpx.post(url, headers=headers, json=payload, timeout=float(MODEL_TIMEOUT_SEC))
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return str(data[0].get("generated_text", "")).strip()
                elif isinstance(data, dict):
                    return str(data.get("generated_text", "")).strip()
            else:
                logger.warning("[HF Free Story] HTTP %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.error("[HF Free Story Error] %s: %s", model, exc)

    return None


# --------------------------------------------------------------------------
# HF Router (paid) — vision
# --------------------------------------------------------------------------

def call_hf_router_vision(image: Image.Image, model: str = WAYSIDE_VISION_MODEL) -> Optional[dict]:
    """Call Hugging Face Router Inference API for image labeling. Requires credits."""
    b64_img = pil_to_base64_jpeg(image)
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    url = f"{HF_ROUTER_BASE.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": LABEL_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ],
        "max_tokens": 60,
        "temperature": 0.2
    }

    try:
        with httpx.Client(timeout=float(MODEL_TIMEOUT_SEC)) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return parse_label_json(content)
            elif resp.status_code == 402:
                logger.error("[HF Router Vision] HTTP 402: No credits. Switch to WAYSIDE_VISION_PROVIDER=hf for free tier.")
            elif resp.status_code == 403:
                logger.error("[HF Router Vision] HTTP 403: Token lacks Inference Providers permission.")
            else:
                logger.warning("[HF Router Vision] HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[HF Router Vision Error] %s", exc)

    return None


# --------------------------------------------------------------------------
# HF Router (paid) — story
# --------------------------------------------------------------------------

def call_hf_router_story(prompt: str, model: str = WAYSIDE_STORY_MODEL) -> Optional[str]:
    """Call Hugging Face Router Inference API for story text generation. Requires credits."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    url = f"{HF_ROUTER_BASE.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 220,
        "temperature": 0.7
    }

    try:
        with httpx.Client(timeout=float(MODEL_TIMEOUT_SEC)) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            elif resp.status_code == 402:
                logger.error("[HF Router Story] HTTP 402: No credits. Switch to WAYSIDE_STORY_PROVIDER=hf for free tier.")
            else:
                logger.warning("[HF Router Story] HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[HF Router Story Error] %s", exc)

    return None


# --------------------------------------------------------------------------
# Keep legacy names pointing to router for backward compatibility
# --------------------------------------------------------------------------
def call_hf_vision(image: Image.Image, model: str = WAYSIDE_VISION_MODEL) -> Optional[dict]:
    """Legacy name — tries free serverless first, then router."""
    return call_hf_free_vision(image) or call_hf_router_vision(image, model)


def call_hf_story(prompt: str, model: str = WAYSIDE_STORY_MODEL) -> Optional[str]:
    """Legacy name — tries free serverless first, then router."""
    return call_hf_free_story(prompt) or call_hf_router_story(prompt, model)

