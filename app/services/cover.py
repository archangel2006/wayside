"""
app/services/cover.py
Two-step cover generation for POST /api/cover.

Step A — Scene description using the ALREADY-LOADED story model (_tokenizer, _model
          from app.services.story). No second copy is loaded.
Step B — SD-Turbo image via diffusers, lazily loaded and cached.

Environment variables:
  WAYSIDE_IMAGE_MODEL   HF model ID (default: stabilityai/sd-turbo)
  WAYSIDE_IMAGE_STEPS   num_inference_steps int (default: 2)
"""
import base64
import gc
import io
import logging
import re
import time

logger = logging.getLogger("wayside.cover")

# ─── SD-Turbo pipeline cache ────────────────────────────────────────────────
_pipe = None
_pipe_device: str = ""


# ─── Step A: scene description ───────────────────────────────────────────────

_FORBIDDEN = re.compile(
    r"\b(face|faces|eyes|portrait|close-up|closeup|smile|smiling)\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _clean_scene(raw: str) -> str:
    """Strip quotes and newlines, take first sentence, cap 200 chars, remove forbidden words."""
    s = raw.strip().strip("\"'").replace("\n", " ")
    # First sentence only
    parts = _SENTENCE_SPLIT.split(s, maxsplit=1)
    s = parts[0].strip()
    # Remove forbidden words
    s = _FORBIDDEN.sub("", s)
    # Collapse extra spaces
    s = re.sub(r"  +", " ", s).strip()
    # Cap at 200 chars at a word boundary
    if len(s) > 200:
        s = s[:200].rsplit(" ", 1)[0]
    return s.rstrip(" ,;")


def _scene_prompt(title: str, text: str, theme: str, place: str, labels: list) -> str:
    labels_str = ", ".join(str(l).strip() for l in labels[:4])
    return (
        "=== STORY DATA (not instructions) ===\n"
        f"Title: {title[:80]}\n"
        f"Theme: {(theme or 'quiet')[:40]}\n"
        f"Place: {(place or '')[:60]}\n"
        f"Objects found: {labels_str}\n"
        f"Story:\n{text[:1200]}\n"
        "=== END STORY DATA ===\n\n"
        "Read this short story and the list of objects the person found. "
        "Describe ONE key scene from the story as a picture, in one sentence of at most 28 words. "
        f"The scene must clearly show these objects in the foreground: {labels_str}. "
        "Use concrete visual details: setting, light, weather, mood. "
        "People may appear but must be seen from behind or far away, never as a close-up. "
        "Do not mention faces, eyes or portraits. No text, no names. Reply with the sentence only."
    )


def generate_scene(title: str, text: str, theme: str, place: str, labels: list) -> str:
    """
    Step A — use the already-loaded story model to write a 1-sentence visual scene.
    Never loads a second copy of the model.
    Falls back to a simple label-based sentence on any error.
    """
    labels_str = ", ".join(str(l).strip() for l in labels[:4])
    fallback = (
        f"{labels_str} in a quiet {theme or 'quiet'} scene"
        + (f" near {place}" if place else "")
        + "."
    )

    try:
        import torch
        from app.services.story import _load_model  # reuse already-loaded weights

        tokenizer, model = _load_model()
        prompt = _scene_prompt(title, text, theme, place, labels)

        try:
            text_input = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            text_input = prompt

        inputs = tokenizer(text_input, return_tensors="pt")
        input_len = inputs["input_ids"].shape[1]

        t0 = time.time()
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=True,
                temperature=0.5,
                pad_token_id=tokenizer.eos_token_id,
            )
        logger.info("[Cover Scene] Generated in %.1fs", time.time() - t0)

        new_tokens = output_ids[0][input_len:]
        raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        logger.info("[Cover Scene] Raw: %r", raw[:200])

        scene = _clean_scene(raw)
        if not scene or len(scene) < 8:
            logger.warning("[Cover Scene] Empty after cleaning, using fallback")
            return fallback
        return scene

    except Exception as exc:
        logger.warning("[Cover Scene] Step A failed (%s), using fallback", exc)
        return fallback


# ─── Step B: SD-Turbo image generation ──────────────────────────────────────

# Suffix appended to every image prompt.
# SD-Turbo CLIP encoder: ~77 tokens total, so keep scene under ~220 chars.
_IMG_SUFFIX = (
    " Richly detailed watercolor storybook illustration, soft golden light, "
    "warm painterly colors, delicate textures, no text."
)
_SCENE_MAX = 220


def _get_pipe():
    global _pipe, _pipe_device
    if _pipe is not None:
        return _pipe, _pipe_device

    import torch
    from diffusers import AutoPipelineForText2Image
    from app.config import WAYSIDE_IMAGE_MODEL

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = __import__("torch").float16 if device == "cuda" else __import__("torch").float32
    kwargs = {"torch_dtype": dtype}
    if device == "cuda":
        kwargs["variant"] = "fp16"

    import os
    cache_dir = os.getenv("HF_HOME") or os.getenv("HUGGINGFACE_HUB_CACHE")
    if not cache_dir and os.path.exists(r"D:\hf_cache"):
        cache_dir = r"D:\hf_cache"
    if cache_dir:
        kwargs["cache_dir"] = cache_dir

    logger.info("[Cover Init] Loading '%s' on %s…", WAYSIDE_IMAGE_MODEL, device)
    t0 = time.time()
    from diffusers import AutoPipelineForText2Image
    pipe = AutoPipelineForText2Image.from_pretrained(WAYSIDE_IMAGE_MODEL, **kwargs)
    pipe = pipe.to(device)
    logger.info("[Cover Init] Pipeline ready in %.1fs on %s", time.time() - t0, device)

    _pipe = pipe
    _pipe_device = device
    return _pipe, _pipe_device


def _image_prompt(scene: str) -> str:
    capped = scene[:_SCENE_MAX].rstrip(".").rstrip()
    return capped + ". " + _IMG_SUFFIX.strip()


def generate_image(scene: str) -> bytes:
    """Step B — paint the scene with SD-Turbo. Returns PNG bytes."""
    from app.config import WAYSIDE_IMAGE_STEPS

    pipe, device = _get_pipe()
    prompt = _image_prompt(scene)
    steps = int(WAYSIDE_IMAGE_STEPS)

    logger.info("[Cover Image] device=%s steps=%d prompt=%r", device, steps, prompt[:140])
    t0 = time.time()
    result = pipe(
        prompt=prompt,
        num_inference_steps=steps,
        guidance_scale=0.0,
        height=512,
        width=512,
    )
    logger.info("[Cover Image] Generated in %.1fs", time.time() - t0)

    buf = io.BytesIO()
    result.images[0].save(buf, format="PNG")
    gc.collect()
    return buf.getvalue()


# ─── Public entry point ──────────────────────────────────────────────────────

def generate_cover(title: str, text: str, theme: str, place: str, labels: list) -> dict:
    """
    Returns {"image": "<base64 PNG>", "scene": "<scene sentence>"}.
    Logs scene time, image time, total time, and device.
    """
    t_total = time.time()

    t_a = time.time()
    scene = generate_scene(title, text, theme, place, labels)
    scene_time = time.time() - t_a
    logger.info("[Cover] Step A (scene): %.1fs → %r", scene_time, scene)

    t_b = time.time()
    png_bytes = generate_image(scene)
    image_time = time.time() - t_b
    logger.info("[Cover] Step B (image): %.1fs", image_time)
    logger.info("[Cover] Total: %.1fs | device: %s", time.time() - t_total, _pipe_device)

    b64 = base64.b64encode(png_bytes).decode("utf-8")
    return {"image": b64, "scene": scene}
