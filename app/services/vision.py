"""
app/services/vision.py
Real find labeling using vision providers or a local VLM.

Environment variables:
  WAYSIDE_VISION_PROVIDER  Provider: "hf" (free HF API), "hf-router" (paid router),
                           "openai" (OpenAI-compatible), "fallback", or "local" (default)
  WAYSIDE_VISION_MODEL     Model ID (used by hf-router / openai providers)

The service is fully lazy-loaded — the model is only instantiated on first request,
so server startup remains fast.

Provider "hf" uses the free HF Serverless Inference API (image-to-text pipeline)
— no credits needed. Falls back to caption-based labeling using BLIP or ViT-GPT2.

Output contract:
  {"label": "<2-4 words>", "description": "<one short playful phrase, under 8 words>"}
  Falls back to {"label": "Mystery find", "description": "hard to say"} on any failure.
"""
import gc
import io
import json
import logging
import re
import time
from PIL import Image

logger = logging.getLogger("wayside.vision")

_processor = None
_model = None
_model_name = None

LABEL_PROMPT = (
    "You are labeling an object a person found on a walk. "
    "Reply with JSON only, no other text, in this exact shape: "
    '{"label": "<2 to 4 words>", "description": "<one short, playful phrase, under 8 words>"} '
    "Name the main object only. If you are unsure, give your best short guess."
)

FALLBACK = {"label": "Mystery find", "description": "hard to say"}


def _load_model():
    global _processor, _model, _model_name
    from app.config import WAYSIDE_VISION_MODEL
    if _model is None:
        import torch
        from transformers import AutoProcessor, AutoModelForVision2Seq

        logger.info("[Vision Init] Loading vision model '%s' from local cache...", WAYSIDE_VISION_MODEL)
        t0 = time.time()
        try:
            _processor = AutoProcessor.from_pretrained(WAYSIDE_VISION_MODEL, local_files_only=True)
            _model = AutoModelForVision2Seq.from_pretrained(
                WAYSIDE_VISION_MODEL,
                dtype=torch.float32,
                local_files_only=True,
            )
            _model.eval()
            _model_name = WAYSIDE_VISION_MODEL
            logger.info("[Vision Init Success] Model loaded in %.1fs", time.time() - t0)
        except Exception as exc:
            logger.warning("[Vision Init] Local model '%s' not cached or incomplete (%s). Using fallback.", WAYSIDE_VISION_MODEL, exc)
            raise
    return _processor, _model


def _parse_label_json(text: str) -> dict:
    """Defensively extract label JSON from raw model output."""
    # Strip code fences
    text = re.sub(r"```[a-zA-Z]*", "", text).strip()
    # Find first {...}
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


def label_image(image: Image.Image) -> dict:
    """
    Sends an image to the vision model and returns {label, description}.
    Falls back to FALLBACK on any error.
    """
    from app.config import WAYSIDE_VISION_PROVIDER, WAYSIDE_VISION_MODEL

    # Downscale to max 512px for speed and memory
    max_dim = max(image.size)
    if max_dim > 512:
        scale = 512.0 / max_dim
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.Resampling.LANCZOS
        )

    # Ensure RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # 1. External providers (no local model loaded into RAM)
    if WAYSIDE_VISION_PROVIDER in ("hf", "huggingface"):
        # Free serverless HF pipeline (BLIP / ViT-GPT2) — no credits needed
        from app.services.providers import call_hf_free_vision
        res = call_hf_free_vision(image)
        return res if res is not None else FALLBACK

    if WAYSIDE_VISION_PROVIDER in ("hf-router",):
        # Paid HF Router — requires credits
        from app.services.providers import call_hf_router_vision
        res = call_hf_router_vision(image, model=WAYSIDE_VISION_MODEL)
        return res if res is not None else FALLBACK

    if WAYSIDE_VISION_PROVIDER in ("openai", "openai-compatible"):
        from app.services.providers import call_openai_compatible_vision
        res = call_openai_compatible_vision(image, model=WAYSIDE_VISION_MODEL)
        return res if res is not None else FALLBACK

    if WAYSIDE_VISION_PROVIDER in ("fallback", "mock"):
        return FALLBACK

    # 2. Local provider (loads transformers model on CPU)
    try:
        import torch
        processor, model = _load_model()

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": LABEL_PROMPT},
                ],
            }
        ]
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt, images=[image], return_tensors="pt")

        t0 = time.time()
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=60,
                do_sample=False,
                temperature=1.0,
            )
        elapsed = time.time() - t0
        logger.info("[Vision Inference] Generated in %.1fs", elapsed)

        # Decode only newly generated tokens
        input_len = inputs["input_ids"].shape[1]
        new_tokens = output_ids[0][input_len:]
        raw = processor.decode(new_tokens, skip_special_tokens=True).strip()
        logger.info("[Vision Output] Raw: %r", raw[:200])

        result = _parse_label_json(raw)
        if result is None:
            # Retry once: just parse any JSON-like substring
            result = _parse_label_json(raw.replace("'", '"'))
        if result is None:
            logger.warning("[Vision Parse Fail] Could not parse JSON, using fallback")
            return FALLBACK

        gc.collect()
        return result

    except Exception as exc:
        logger.error("[Vision Error] %s", exc, exc_info=True)
        gc.collect()
        return FALLBACK
