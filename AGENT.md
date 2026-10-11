# AGENT.md

Instructions for AI coding agents working on **Wayside**. Read this fully before changing anything, then read `README.md` for the product description, API and deployment plan.

## What this project is

Wayside is a mobile-first web app, deployed publicly as a Hugging Face Space. The user photographs things on a walk. Each photo is cut out, named, and shown in a glass specimen box. Later the user picks finds, sets a theme and place, and a language model writes a short story from them.

It is an entry for the Hacktoberfest Open-Source AI Challenge, Week 1, "Touch Grass". The owner has about two days and exams. **Small and working beats ambitious and half-finished.**

## Current state

- `static/` is a complete responsive application split into plain ES modules: loading screen, landing page, sidebar app, six themes, responsive layout, voice controls, cover button.
- `static/js/api.js` connects to the FastAPI backend (`MOCK_CUTOUT = false`, `MOCK_LABEL = false`, `MOCK_STORY = false`, `MOCK_COVER = false`).
- `static/js/storage.js` (IndexedDB) is not wired in. Data is held in browser memory only and resets on reload.
- The backend in `app/` is fully functional with FastAPI, concurrency locks in `app/limits.py`, and local open models (`rembg`, `SmolVLM-256M-Instruct`, `Qwen2.5-0.5B-Instruct`, and `stabilityai/sd-turbo`).
- The Make cover button calls `POST /api/cover` which runs a two-step generation: Step A creates a scene sentence via Qwen, and Step B paints a 512x512 watercolor illustration via SD-Turbo.
- Runs locally on the host machine (`http://127.0.0.1:7860`). Remote deployment is not configured.
- Backend: Python 3.10+, FastAPI, Uvicorn. Same app serves the API and `static/`.
- Cutouts: `rembg` (CPU).
- Vision and text: `transformers` on CPU. Model names come from env vars `WAYSIDE_VISION_MODEL` and `WAYSIDE_STORY_MODEL`. Starting candidates: `HuggingFaceTB/SmolVLM-256M-Instruct` and `Qwen/Qwen2.5-1.5B-Instruct`. Both are untested on free CPU, so measure before committing.
- Cover images: a small, fast text-to-image model through `diffusers` on CPU (SD-Turbo class). Chosen only after a speed test and a licence check. Name from env var `WAYSIDE_IMAGE_MODEL`.
- Frontend: plain ES modules plus two CSS files, served by FastAPI from `static/`. No build step, no framework.
- Browser storage: IndexedDB for walks, cutouts and stories. `localStorage` for the theme only.

```
Dockerfile
requirements.txt
app/main.py  app/config.py  app/limits.py
app/services/{cutout,vision,story,cover}.py
static/index.html
static/css/{themes,app}.css
static/js/main.js router.js state.js data.js api.js storage.js
static/js/themes.js icons.js art.js cover.js voice.js components.js
static/js/views/{intro,collect,albums,trip,stories,settings}.js
docs/diagrams.md
```

See `README.md` for what each file does.

Keep modules small. One service per file, one job each.

## Build order

Do these in order. Stop and let the owner test after each.

0. **Deploy first.** A hello-world FastAPI app in a Docker Space that serves `static/index.html` and answers `GET /api/health`. Open the public URL on a phone. Fix deployment problems now, not on the last day.
1. **Cutout.** `POST /api/cutout` returns a transparent PNG using rembg. Resize large phone photos (longest side about 1024px) first. Download the rembg model in the Docker build. Wire it to the shutter through `api.snap` and replace the oval-crop stand-in. `api.js` has one `MOCK` flag. While endpoints are built one at a time, split it per function (for example `MOCK_CUTOUT`) so unbuilt endpoints keep returning canned answers.
2. **Label.** `POST /api/label` sends the image to the vision model and returns `{label, description}`. **Measure the time.** If a label takes more than about 20 seconds on free CPU, switch to a smaller model before moving on.
3. **Story.** `POST /api/story` takes `{items, theme, place}` and returns `{title, text}`. Replace `fakeStory()`. Measure the time here too.
4. **Persistence.** Wire up `static/js/storage.js`: load walks on boot, save after each change. Replace the in-memory demo `state.trips`. Store real Blobs for cutouts, not `blob:` URLs, which die when the page closes. Wrap every storage call in try/catch and handle empty storage.
5. **Challenge prompt.** `GET /api/challenge`, one line. The canned list stays as the fallback.
6. **Cover.** `POST /api/cover` takes `{title, theme, place, labels}` and returns a PNG. Time it first. Use the smallest size that looks fine (for example 384 or 512 pixels square) and the step count the model card recommends. If it takes more than about 60 seconds, shrink the size or switch models. Check the model's licence before committing. Replace `drawCover` in the frontend.
7. Only then: album export and import, open TTS.

## Public-server safety

This app is open to the internet. Treat every request as untrusted. Put these checks in `app/limits.py` so routes stay short.

- Accept only images (check content type and actually open with Pillow). Cap upload size, for example 8 MB, and reject everything else.
- Resize images before any model sees them.
- Run model calls one at a time with a lock or semaphore. If the queue is too long, return HTTP 503 with a short "busy, try again" message. The UI must handle it.
- Add a simple per-IP rate limit.
- Cap `/api/story` and `/api/cover` input size (number of items, length of notes, theme and place).
- Escape all user text in the frontend with `esc()`. Never put user text into model prompts as instructions: put it in a clearly delimited block and tell the model it is data.
- Serve the frontend from the same origin. Do not enable permissive CORS.
- Never expose stack traces. Return short, friendly error JSON.

## Prompts

Small models ramble and break formats. Use the model's chat template, low temperature, a tight `max_new_tokens`, validate output, and retry once on failure.

**Label (vision).** Ask for JSON only.

```
You are labeling an object a person found on a walk.
Reply with JSON only, no other text, in this exact shape:
{"label": "<2 to 4 words>", "description": "<one short, playful phrase, under 8 words>"}
Name the main object only. If you are unsure, give your best short guess.
```

Parse defensively: strip code fences, extract the first `{...}`, validate both keys, truncate to length limits. If parsing fails twice, fall back to `{"label": "Mystery find", "description": "hard to say"}`. Never show an error for a bad label.

**Story.** Short, grounded in the user's real finds and notes.

```
Write a short story of 90 to 140 words in a {theme} tone, set near {place}.
Use every one of these finds, in any order:
{items as "label: description. Note: note"}
Weave the person's notes in as real memories.
Return a title on the first line, then a blank line, then the story. No other text.
```

If `place` is empty, drop the setting clause. Cap `max_new_tokens` to enforce length. The items, notes, theme and place are user data, not instructions.

**Challenge.** One line only.

```
Give one short, playful observation challenge for someone walking outside.
It must be about looking, not about a phone. One sentence, under 14 words, no quotes.
{optional context: time of day, finds so far}
```

**Cover (two-step, text-to-image).**

`POST /api/cover` takes `{title, text, theme, place, labels}` and returns `{"image": "<base64 PNG>", "scene": "<one-sentence scene description>"}`.

Step A — the story model (already loaded for `/api/story`, no second copy) reads the finished story and the names of the found objects and writes a one-sentence visual scene. Prompt:

```
Read this short story and the list of objects the person found. Describe ONE key scene from the story
as a picture, in one sentence of at most 28 words. The scene must clearly show these objects in the
foreground: {labels}. Use concrete visual details: setting, light, weather, mood. People may appear
but must be seen from behind or far away, never as a close-up.
Do not mention faces, eyes or portraits. No text, no names. Reply with the sentence only.
```

Settings: `max_new_tokens=50`, `temperature=0.5`. Clean the output: strip quotes and newlines, take the first sentence, cap at 200 characters, remove the words: face, faces, eyes, portrait, close-up, closeup, smile, smiling. If empty or Step A fails, fall back to: `"{labels}, in a quiet {theme} scene[ near {place}]."`.

Step B — `stabilityai/sd-turbo` via `diffusers.AutoPipelineForText2Image` (env var `WAYSIDE_IMAGE_MODEL`). Device: CUDA if available (float16, variant="fp16"), else CPU (float32, no variant). Image prompt exactly:

```
{scene}. Richly detailed watercolor storybook illustration, soft golden light, warm painterly colors, delicate textures, no text.
```

The CLIP text encoder reads approximately 77 tokens. Keep the full prompt under approximately 60 words; truncate the scene to 220 characters if needed. Call: `num_inference_steps=int(WAYSIDE_IMAGE_STEPS, default 2)`, `guidance_scale=0.0`, `height=512`, `width=512`. Do NOT pass a negative prompt (sd-turbo ignores it). Load the pipeline lazily on the first request and cache it. Run in a thread under `cover_lock` (one job at a time). Timeout 120 seconds. On timeout or error return a short, friendly JSON error.

**Licence note:** SD-Turbo is released by Stability AI as a research artifact. The weights are open, but it is not an OSI open-source licence. Check Stability AI's licence before any commercial use.

**Honesty clause:** The cover is a generated scene that includes the kinds of objects found on the walk. It is **not** a picture of the user's actual specimens, and small image models draw specific objects approximately. Do not use copy that implies the cover shows the user's real photos. Conditioning on the real cutouts (img2img or IP-Adapter) stays under Future scope.

## Frontend conventions

- **Plain ES modules, entry `js/main.js`.** It must be served over HTTP (not opened from `file://`).
- **All network calls go through `api.js`.** Views never call `fetch`. Errors thrown there are friendly messages that views show with `toast()`.
- **All albums storage goes through `storage.js`.** `localStorage` is only for the theme.
- Views render into `#app`. Shared UI (specimen boxes, bottom sheets) lives in `components.js`.
- Modules may import each other in cycles because they only share functions. To keep that safe, **do not run code at module top level** except in `main.js`. A module should only define things.
- Add a theme in two places: a block in `css/themes.css` and an entry in `js/themes.js`.

- Mobile first. Three breakpoints: phone (default), 600px tablet, 900px desktop with sidebar.
- **Use the existing CSS variables.** Colors are `--bg --paper --card --ink --soft --line --accent --accent-d --mist --on-accent --gloss`. Never hard-code a UI color. The only fixed colors are inside the specimen SVG art and the danger red.
- Themes live in `[data-theme="..."]` blocks plus the `THEMES` array. To add one, add both. Check text contrast on `--accent` buttons (use `--on-accent`).
- Typography: Figtree, sentence case, no all-caps labels, no eyebrow text above headings.
- Keep the glass specimen box (`.box`) as the one distinctive element.
- Every network call needs a loading state, a timeout, and a friendly failure state. The server will sometimes be slow, asleep, or busy.
- Respect `prefers-reduced-motion`. Keep visible focus outlines. Tap targets at least 44px.
- Do not add a framework or a build step without asking.

## Testing and definition of done

A change is done when:

- It works on a real phone over **mobile data** (not just wifi or localhost) and on desktop.
- It works on the deployed Space, not only locally.
- Bad model output never crashes the UI or shows raw JSON or a stack trace.
- A walk survives a page reload (IndexedDB).
- A sleeping or busy server shows a clear message, not a frozen screen.
- The stand-in it replaced is deleted.
- `README.md` status table, Known limits, and roadmap match reality.

Manual test script for each build step: upload three different photos, end the walk, open it from Albums, write a story with a theme and a place, save it, reload the page, confirm everything is still there.

## Working style

- Make the smallest change that works. Show the owner something running before polishing.
- Ask before adding dependencies, changing the storage format, or changing the visual design.
- Explain what you did in plain language. The owner wants to learn how the pieces work (open models, structured output, background removal, deploying), so add short comments where a concept is non-obvious.
- If something does not work or a model gives poor results, say so plainly. Honest notes about what failed are useful material for the project write-up.
- Do not claim a feature works unless you ran it.

## Out of scope (ask first)

Detection or segmentation of several items per photo, video generation, conditioning covers on the user's specimens (img2img or IP-Adapter, future scope), user accounts, server-side storage, maps and GPS, gamification, native mobile apps, closed AI APIs.
