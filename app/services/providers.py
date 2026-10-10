"""
app/services/providers.py
External inference provider abstraction for vision labeling and story generation.

Supports:
- "hf" / "huggingface": Hugging Face Serverless / Router Inference API
- "openai": OpenAI-compatible endpoints (Groq, Together, OpenRouter, vLLM, Ollama)
- "fallback": Instant offline heuristic fallback

Maintains identical response contracts:
- Vision: {"label": str, "description": str}
- Story:  {"title": str, "text": str}
"""
import base64
import io
import json
import logging
import re
from typing import Optional
from PIL import Image

import httpx

from app.config import (
    HF_TOKEN,
    HF_API_BASE,
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    WAYSIDE_VISION_MODEL,
    WAYSIDE_STORY_MODEL,
    MODEL_TIMEOUT_SEC,
)

logger = logging.getLogger("wayside.providers")

LABEL_PROMPT = (
    "You are labeling an object a person found on a walk. "
    "Reply with JSON only, no other text, in this exact shape: "
    '{"label": "<2 to 4 words>", "description": "<one short, playful phrase, under 8 words>"} '
    "Name the main object only. If you are unsure, give your best short guess."
)


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


def parse_label_json(text: str) -> Optional[dict]:
    """Defensively extract label JSON from raw model output."""
    if not text:
        return None
    text = re.sub(r"```[a-zA-Z]*", "", text).strip()
    m = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        label = str(obj.get("label", "")).strip()[:60]
        description = str(obj.get("description", "")).strip()[:80]
        if label and description:
            return {"label": label, "description": description}
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def parse_story_text(raw: str, fallback_title: str) -> Optional[dict]:
    """Parse raw LLM output into title and story text."""
    if not raw:
        return None
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
    if len(lines) >= 2:
        title = lines[0].strip("#").strip()
        text = "\n".join(lines[1:]).strip()
    elif len(lines) == 1:
        title = fallback_title
        text = lines[0]
    else:
        return None

    if len(title) > 120:
        title = fallback_title

    return {"title": title, "text": text}


def call_hf_vision(image: Image.Image, model: str = WAYSIDE_VISION_MODEL) -> Optional[dict]:
    """Call Hugging Face Serverless / Router Inference API for image labeling."""
    b64_img = pil_to_base64_jpeg(image)
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    # Try standard HF chat completions endpoint
    url = "https://api-inference.huggingface.co/v1/chat/completions"
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
            else:
                logger.warning("[HF Vision API] HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[HF Vision API Error] %s", exc)

    return None


def call_openai_compatible_vision(image: Image.Image, model: str = WAYSIDE_VISION_MODEL) -> Optional[dict]:
    """Call an OpenAI-compatible vision endpoint (e.g. Groq, Together, Ollama, OpenRouter)."""
    b64_img = pil_to_base64_jpeg(image)
    headers = {"Content-Type": "application/json"}
    if OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"

    base = OPENAI_API_BASE.rstrip("/")
    url = f"{base}/chat/completions"
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
            else:
                logger.warning("[OpenAI Vision API] HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[OpenAI Vision API Error] %s", exc)

    return None


def call_hf_story(prompt: str, model: str = WAYSIDE_STORY_MODEL) -> Optional[str]:
    """Call Hugging Face Inference API for story text generation."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    # Try chat completions endpoint first
    url = "https://api-inference.huggingface.co/v1/chat/completions"
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
            
            # Fallback to model-specific endpoint
            model_url = f"{HF_API_BASE.rstrip('/')}/{model}"
            resp2 = client.post(
                model_url,
                headers=headers,
                json={"inputs": prompt, "parameters": {"max_new_tokens": 220, "temperature": 0.7, "return_full_text": False}}
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                if isinstance(data2, list) and len(data2) > 0:
                    return data2[0].get("generated_text", "")
            else:
                logger.warning("[HF Story API] HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[HF Story API Error] %s", exc)

    return None


def call_openai_compatible_story(prompt: str, model: str = WAYSIDE_STORY_MODEL) -> Optional[str]:
    """Call OpenAI-compatible endpoint for story generation."""
    headers = {"Content-Type": "application/json"}
    if OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"

    base = OPENAI_API_BASE.rstrip("/")
    url = f"{base}/chat/completions"
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
            else:
                logger.warning("[OpenAI Story API] HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[OpenAI Story API Error] %s", exc)

    return None
