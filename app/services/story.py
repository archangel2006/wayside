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

        logger.info("[Story Init] Loading story model '%s' from local cache...", WAYSIDE_STORY_MODEL)
        t0 = time.time()
        try:
            _tokenizer = AutoTokenizer.from_pretrained(WAYSIDE_STORY_MODEL, local_files_only=True)
            _model = AutoModelForCausalLM.from_pretrained(
                WAYSIDE_STORY_MODEL,
                dtype=torch.float32,
                local_files_only=True,
            )
            _model.eval()
            _model_name = WAYSIDE_STORY_MODEL
            logger.info("[Story Init Success] Model loaded from cache in %.1fs", time.time() - t0)
        except Exception as exc:
            logger.warning("[Story Init] Local model '%s' not cached or incomplete (%s). Using fallback.", WAYSIDE_STORY_MODEL, exc)
            raise
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
        f"You are a gifted storyteller writing an evocative, atmospheric short tale (100 to 150 words).\n"
        f"Tone and atmosphere: {theme.capitalize()}{setting_clause}.\n"
        f"Weave these curious finds and memories seamlessly into the scene:\n"
        f"{items_block}\n"
        f"Use vivid sensory details, emotional resonance, and creative imagery to bring the walk to life.\n"
        f"Format:\n"
        f"Line 1: A creative, evocative Title\n"
        f"Line 2: (blank)\n"
        f"Line 3+: The story text. Return nothing else."
    )
    return prompt


def _fallback_story(items: list, theme: str, place: str) -> dict:
    theme = (theme or "quiet").lower()
    place_str = f"Near {place}" if place else "Along the wandering trail"

    # Theme-adaptive atmospheric opening and sensory adjectives
    moods = {
        "quiet": ("a hush fell over the afternoon, soft as falling dust", "whispering secrets to the quiet earth"),
        "playful": ("the day sparkled with unexpected mischief", "dancing lightly under the playful breeze"),
        "mysterious": ("shadows stretched long and every corner held a forgotten riddle", "waiting like ancient clues in the stillness"),
        "gloomy": ("mist hung low like a sleepy breath over the path", "resting cold and silent beneath gray skies"),
        "curious": ("every stone and leaf seemed to have something urgent to say", "inviting closer inspection with quiet intrigue"),
        "bright": ("golden light spilled through the leaves in warm patches", "gleaming warmly under the open sky")
    }
    mood_open, mood_close = moods.get(theme, moods["quiet"])

    if items:
        main_item = items[0]
        title = f"The {theme.capitalize()} Chronicle of the {main_item.get('label', 'Wayside Find')}"

        item_descriptions = []
        for it in items[:4]:
            lbl = it.get("label", "a small find")
            desc = it.get("description", "").strip()
            note = it.get("note", "").strip()
            detail = f"{lbl}"
            if desc:
                detail += f", {desc}"
            if note:
                detail += f" ({note})"
            item_descriptions.append(detail)

        finds_narrative = "; beside it lay ".join(item_descriptions)
        text = (
            f"{place_str}, {mood_open}. "
            f"Wandering with open eyes brought curious discoveries to light: there was {finds_narrative}. "
            f"Each relic seemed to carry its own quiet memory, {mood_close}. "
            f"You tucked the impressions into your thoughts like treasures in a pocket, returning home with the world feeling just a little more wondrous."
        )
    else:
        title = f"A {theme.capitalize()} Stroll {place_str}"
        text = (
            f"{place_str}, {mood_open}. "
            f"The trail was still, but the ground was alive with quiet wonders, {mood_close}. "
            f"You carried the feeling home in your head, a little more {theme} than when you set out."
        )

    return {"title": title, "text": text}


def generate_story(items: list, theme: str, place: str) -> dict:
    """
    Generates an imaginative short story from items, theme, and place.
    Returns {"title": str, "text": str}.
    Falls back to a dynamic theme-based template story on any error.
    """
    from app.config import WAYSIDE_STORY_PROVIDER, WAYSIDE_STORY_MODEL
    from app.services.providers import parse_story_text

    fallback = _fallback_story(items, theme, place)
    prompt = _build_prompt(items, theme, place)

    # 1. External providers (no local model loaded into RAM)
    if WAYSIDE_STORY_PROVIDER in ("hf", "huggingface"):
        # Free serverless HF pipeline — no credits needed
        from app.services.providers import call_hf_free_story
        raw = call_hf_free_story(prompt)
        parsed = parse_story_text(raw, fallback["title"]) if raw else None
        return parsed if parsed is not None else fallback

    if WAYSIDE_STORY_PROVIDER in ("hf-router",):
        # Paid HF Router — requires credits
        from app.services.providers import call_hf_router_story
        raw = call_hf_router_story(prompt, model=WAYSIDE_STORY_MODEL)
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
                max_new_tokens=260,
                do_sample=True,
                temperature=0.88,
                top_p=0.92,
                repetition_penalty=1.12,
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
        logger.info("[Story] Local model not available (%s), generated creative narrative via theme engine.", exc)
        gc.collect()
        return fallback
