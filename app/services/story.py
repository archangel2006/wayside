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
        try:
            _tokenizer = AutoTokenizer.from_pretrained(WAYSIDE_STORY_MODEL)
            _model = AutoModelForCausalLM.from_pretrained(
                WAYSIDE_STORY_MODEL,
                dtype=torch.float32,
            )
            _model.eval()
            _model_name = WAYSIDE_STORY_MODEL
            logger.info("[Story Init Success] Model loaded in %.1fs", time.time() - t0)
        except Exception as exc:
            logger.warning("[Story Init] Could not load '%s' (%s). Using dynamic story engine.", WAYSIDE_STORY_MODEL, exc)
            raise
    return _tokenizer, _model


def _build_prompt(items: list, theme: str, place: str) -> str:
    """
    Build the story generation prompt. Instructs the model to write a rich,
    coherent narrative that respects the physical nature of the finds.
    """
    theme = (theme or "quiet").strip()[:40]
    setting = f" near {place}" if place else " during an afternoon walk"

    item_lines = []
    for it in items[:8]:
        label = str(it.get("label", "")).strip()[:40]
        desc = str(it.get("description", "")).strip()[:60]
        note = str(it.get("note", "")).strip()[:80]
        line = f"- {label}"
        if desc and desc.lower() not in ["found on the path", "spotted on the way", "hard to say"]:
            line += f" ({desc})"
        if note:
            line += f': Note: "{note}"'
        item_lines.append(line)
    items_block = "\n".join(item_lines) if item_lines else "- a small wayside treasure"

    
    prompt = (
        f"You are a gifted fiction author. Write an imaginative, coherent short story (160 to 220 words){setting}.\n\n"
        f"Atmosphere & Tone: {theme.capitalize()}, vivid, sensory, and emotionally grounded.\n\n"
        f"Finds & Observations to weave into the scene:\n"
        f"{items_block}\n\n"
        f"Writing Instructions:\n"
        f"1. Write a real narrative with logical continuity—NEVER simply list items or repeat 'beside it lay'.\n"
        f"2. Respect context: atmospheric sights belong in the air, creatures move with agency, and ground items rest underfoot.\n"
        f"3. Weave notes into the protagonist's inner monologue or memories.\n"
        f"4. Structure: An immersive opening, a meaningful discovery sequence, and a lingering, poetic finish. Do NOT include section headers.\n\n"
        f"Format:\n"
        f"Line 1: A creative Title (no quotes)\n"
        f"Line 2: [leave blank]\n"
        f"Line 3+: The story text."
    )
    return prompt


def _fallback_story(items: list, theme: str, place: str) -> dict:
    theme = (theme or "quiet").lower()
    place_name = place.strip() if place else "the trail"

    # Mood-specific settings
    mood_palettes = {
        "quiet": {
            "air": "a stillness so deep you could hear the soft click of branches overhead",
            "light": "pale amber afternoon light filtering softly through the canopy",
            "mood": "contemplative calm",
            "verb": "drifted peacefully"
        },
        "curious": {
            "air": "a crisp breeze full of the scent of turned earth and damp pine",
            "light": "dancing sunbeams highlighting hidden details in the landscape",
            "mood": "gentle intrigue",
            "verb": "stepped with watchful curiosity"
        },
        "playful": {
            "air": "a buoyant breeze carrying the flutter of birds in the trees",
            "light": "golden afternoon glow bouncing warmly off every surface",
            "mood": "lighthearted wonder",
            "verb": "wandered with an easy, adventurous stride"
        },
        "mysterious": {
            "air": "cool air hanging heavy with the silence of forgotten paths",
            "light": "long, shifting shadows stretching across the quiet ground",
            "mood": "enchanting enigma",
            "verb": "moved softly through the stillness"
        },
        "gloomy": {
            "air": "a cool mist curling softly around the damp edges of the trail",
            "light": "a thoughtful gray overcast sky casting a moody tone",
            "mood": "wistful quietude",
            "verb": "walked slowly under the heavy sky"
        }
    }
    palette = mood_palettes.get(theme, mood_palettes["quiet"])

    # Categorize items by natural domain so they make physical and narrative sense
    def categorize(label: str) -> str:
        l = label.lower()
        if any(w in l for w in ["rainbow", "cloud", "sky", "sun", "rain", "mist", "fog", "drizzle", "horizon"]):
            return "sky"
        if any(w in l for w in ["cat", "kitten", "dog", "puppy", "bird", "squirrel", "duck", "butterfly", "bee", "rabbit", "beetle"]):
            return "creature"
        if any(w in l for w in ["leaf", "flower", "tree", "plant", "acorn", "pinecone", "moss", "fern", "petal", "grass", "mushroom", "bark", "branch"]):
            return "flora"
        return "relic"

    vignettes = []
    for it in items[:5]:
        lbl = it.get("label", "").strip()
        cat = categorize(lbl)
        note = it.get("note", "").strip()
        note_str = f' A quiet thought surfaced: "{note}".' if note else ""

        if cat == "sky":
            vignettes.append(
                f"Lifting your eyes above the tree line, {lbl} greeted the afternoon—arching gently across the softening light like an unexpected brushstroke across the heavens.{note_str}"
            )
        elif cat == "creature":
            vignettes.append(
                f"A sudden flicker of motion caught your eye as {lbl} appeared, observing the path with cautious curiosity before settling quietly into the scene.{note_str}"
            )
        elif cat == "flora":
            vignettes.append(
                f"Resting against the damp path was {lbl}, its delicate edges holding the cool moisture of the air like a small token left by the changing season.{note_str}"
            )
        else:
            vignettes.append(
                f"Tucked half-hidden by the roadside, {lbl} caught your attention, bearing the quiet patina of something timeless and undisturbed.{note_str}"
            )

    p1 = f"Near {place_name}, {palette['air']}, and you {palette['verb']} as {palette['light']} warmed the route."
    p2 = " ".join(vignettes) if vignettes else "The trail was peaceful, offering quiet moments of discovery at every turn."
    p3 = (
        f"By the time the afternoon began to lean toward dusk, each sighting had woven itself into a tapestry of {palette['mood']}. "
        f"You carried the memories home like small treasures tucked safely in a pocket, with the world feeling just a little more wondrous and alive."
    )

    full_story = f"{p1}\n\n{p2}\n\n{p3}"
    first_lbl = items[0].get("label", "Wayside Trail") if items else "Wayside Walk"
    title = f"The {theme.capitalize()} Chronicle of the {first_lbl.title()}"

    return {"title": title, "text": full_story}


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
                max_new_tokens=380,
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

        from app.services.providers import _clean_llm_text
        cleaned = _clean_llm_text(raw)

        # Parse: first non-empty line is title, rest is story
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
        if len(lines) >= 2:
            title = lines[0].strip("#").strip()
            text = _clean_llm_text("\n".join(lines[1:]))
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
