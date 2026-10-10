"""
app/services/story.py
Real story generation using a small instruct language model (Qwen2.5-0.5B-Instruct by default).

Environment variable:
  WAYSIDE_STORY_MODEL  Model ID from Hugging Face Hub (default: Qwen/Qwen2.5-0.5B-Instruct)

The service is fully lazy-loaded.

Input contract (from api.js):
  {
    "items": [{"label": str, "description": str, "note": str}],
    "theme": str,
    "place": str
  }

Output contract:
  {"title": str, "text": str}
  Falls back to a simple template story on any failure.
"""
import gc
import logging
import re
import time

logger = logging.getLogger("wayside.story")

_tokenizer = None
_model = None
_model_name = None


def _load_model():
    global _tokenizer, _model, _model_name
    from app.config import WAYSIDE_STORY_MODEL
    if _model is None:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        logger.info("[Story Init] Loading story model '%s'...", WAYSIDE_STORY_MODEL)
        t0 = time.time()
        _tokenizer = AutoTokenizer.from_pretrained(WAYSIDE_STORY_MODEL)
        _model = AutoModelForCausalLM.from_pretrained(
            WAYSIDE_STORY_MODEL,
            torch_dtype=torch.float32,
        )
        _model.eval()
        _model_name = WAYSIDE_STORY_MODEL
        logger.info("[Story Init Success] Model loaded in %.1fs", time.time() - t0)
    return _tokenizer, _model


def _build_prompt(items: list, theme: str, place: str) -> str:
    """
    Build the story generation prompt. User text is in a clearly delimited
    data block so the model treats it as content, not instructions.
    """
    theme = (theme or "quiet").strip()[:40]
    place = (place or "").strip()[:60]

    # Format each item as a data line — user content is NOT part of instructions
    item_lines = []
    for it in items[:8]:  # cap at 8 finds
        label = str(it.get("label", "")).strip()[:40]
        desc = str(it.get("description", "")).strip()[:60]
        note = str(it.get("note", "")).strip()[:80]
        line = f"- {label}: {desc}"
        if note:
            line += f". Note: {note}"
        item_lines.append(line)
    items_block = "\n".join(item_lines) if item_lines else "- a mystery find: hard to say"

    setting_clause = f" set near {place}" if place else ""

    prompt = (
        f"Write a short story of 90 to 140 words in a {theme} tone{setting_clause}.\n"
        f"Use every one of these finds, in any order:\n"
        f"{items_block}\n"
        f"Weave the person's notes in as real memories.\n"
        f"Return a title on the first line, then a blank line, then the story. No other text."
    )
    return prompt


def _fallback_story(items: list, theme: str, place: str) -> dict:
    theme = (theme or "quiet").lower()
    place_str = f"Near {place}, t" if place else "T"
    finds = [it.get("label", "a find") for it in items[:3]]
    text = (
        f"{place_str}he walk had a {theme} feeling, and the ground was full of small stories. "
        + " ".join(f"There was a {f}." for f in finds)
        + f" You carried it all home in your head, a little more {theme} than before."
    )
    title = f"The {theme.capitalize()} Walk" if not items else f"The {theme.capitalize()} Tale of the {items[0].get('label', 'Find')}"
    return {"title": title, "text": text}


def generate_story(items: list, theme: str, place: str) -> dict:
    """
    Generates a short story from items, theme, and place.
    Returns {"title": str, "text": str}.
    Falls back to a template story on any error.
    """
    from app.config import WAYSIDE_STORY_PROVIDER, WAYSIDE_STORY_MODEL
    from app.services.providers import parse_story_text

    fallback = _fallback_story(items, theme, place)
    prompt = _build_prompt(items, theme, place)

    # 1. External providers (no local model loaded into RAM)
    if WAYSIDE_STORY_PROVIDER in ("hf", "huggingface"):
        from app.services.providers import call_hf_story
        raw = call_hf_story(prompt, model=WAYSIDE_STORY_MODEL)
        parsed = parse_story_text(raw, fallback["title"]) if raw else None
        return parsed if parsed is not None else fallback

    if WAYSIDE_STORY_PROVIDER in ("openai", "openai-compatible"):
        from app.services.providers import call_openai_compatible_story
        raw = call_openai_compatible_story(prompt, model=WAYSIDE_STORY_MODEL)
        parsed = parse_story_text(raw, fallback["title"]) if raw else None
        return parsed if parsed is not None else fallback

    if WAYSIDE_STORY_PROVIDER in ("fallback", "mock"):
        return fallback

    # 2. Local provider (loads transformers model on CPU)
    try:
        import torch
        tokenizer, model = _load_model()

        # Build chat message using model's chat template
        prompt = _build_prompt(items, theme, place)
        messages = [{"role": "user", "content": prompt}]

        # Apply chat template if available
        try:
            text_input = tokenizer.apply_chat_template(
                messages,
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
                max_new_tokens=220,
                do_sample=True,
                temperature=0.7,
                repetition_penalty=1.15,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.time() - t0
        logger.info("[Story Inference] Generated in %.1fs", elapsed)

        # Decode only newly generated tokens
        new_tokens = output_ids[0][input_len:]
        raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        logger.info("[Story Output] Raw (first 300 chars): %r", raw[:300])

        # Parse: first line is title, rest is story
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        if len(lines) >= 2:
            title = lines[0].strip("#").strip()
            text = "\n".join(lines[1:]).strip()
        elif len(lines) == 1:
            title = _fallback_story(items, theme, place)["title"]
            text = lines[0]
        else:
            return _fallback_story(items, theme, place)

        # Sanity: if title is too long it's probably story text
        if len(title) > 120:
            title = _fallback_story(items, theme, place)["title"]

        gc.collect()
        return {"title": title, "text": text}

    except Exception as exc:
        logger.error("[Story Error] %s", exc, exc_info=True)
        gc.collect()
        return _fallback_story(items, theme, place)
