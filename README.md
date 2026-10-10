---
title: Wayside
emoji: 🍂
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Wayside

**Collect your walk.**

Wayside turns a walk into a collection. You snap the odd little things you pass (an eerie leaf, a random dog, a candy wrapper), and Wayside cuts each one out, names it, and pins it in a glass box like a butterfly specimen. Back home, you pick finds, add a theme and a place, and get a short story built from your real walk.

Built for the **Hacktoberfest Open-Source AI Challenge, Week 1: "Touch Grass"**. The screen is the shortest part of the experience. The walk is where the project happens.

---

## Status

Be clear about what is real.

| Part | State |
|---|---|
| Frontend (all pages, six themes, responsive layout, voice controls, cover button) | Working prototype, split into plain ES modules under `static/` |
| Cutouts, labels, stories, challenge prompts | **Stand-in answers in the frontend. Not AI yet.** |
| Backend (FastAPI + open models on a Hugging Face Space) | Planned, specified below |
| Saving albums in the browser (IndexedDB) | `static/js/storage.js` is written but **not wired in**. The prototype keeps everything in memory. |
| Story cover images (small open text-to-image model) | Planned. The prototype draws a stand-in image so you can see the flow. |
| Voice | Browser built-in voice with pause and resume for now, Piper planned |

---

## How it works

1. **Walk and snap.** A one-line challenge nudges you to look closer ("find something smaller than your thumbnail"). Stuck? One tap gives another idea.
2. **Pin it in glass.** The background is removed and your find gets a short name and a one-line description in its own box. You can add your own note to any find.
3. **Name the walk.** Ending a walk saves it to your albums.
4. **Read your story.** Tick finds, set a setting and a theme, and a language model writes a short story from your labels and notes. Listen to it (with pause and resume), or save it to the walk's story vault.
5. **Make a cover.** One tap paints a cover image from the story's theme, place and finds, using a small open text-to-image model. The cover is a generated scene, not a picture of your actual specimens.

## Pages

| Page | What it does |
|---|---|
| Loading | Short intro while models "warm up" |
| Landing | What Wayside is, how it works, why open models |
| Collect | Challenge, shutter, shelf for the current walk, End walk |
| Albums | All saved walks with a summary line |
| Trip | A walk's specimen grid, story builder, story vault, story covers |
| Stories | Every story across all walks |
| Settings | Theme picker, model status, replay intro, reset demo data |

The layout adapts to three sizes: phone (bottom tab bar), tablet, and desktop (sidebar with two-pane pages).

## Themes

Moss (default), Tide, Dusk, Blossom, Honey, and Night (dark). The choice is remembered in the browser. All colors are CSS variables on `:root` and `[data-theme="..."]`, so adding a theme is one block of CSS plus one entry in the `THEMES` list.

---

## Why open source AI matters here

Every smart step uses an open-weight model, loaded from the Hugging Face Hub and run on our own Space. There is no closed AI API anywhere in the app.

| Step | Open piece |
|---|---|
| Background removal | [rembg](https://github.com/danielgatis/rembg) (U2-Net) |
| Naming and describing a find | A small open vision-language model, such as SmolVLM |
| Writing stories and challenge prompts | A small open instruct model, such as Qwen2.5-1.5B-Instruct or SmolLM2 |
| Story cover image | A small, fast open text-to-image model (SD-Turbo class), chosen after a speed and licence check |
| Voice (planned) | An open text-to-speech model such as Piper |

The vision, story and image models above are candidates. The final choice depends on a speed test on free CPU and, for the image model, a licence check (see Known limits).

What that gives you, honestly:

- **No closed AI behind the curtain.** Anyone can read which models are used and swap them.
- **Free to run.** Small models on free hosting. No API keys, no cost per photo.
- **Swappable.** Model names are configuration, so a better model can replace a small one without changing the app.
- **Albums stay with you.** Walks, cutouts and stories are saved in your own browser, not in a server database.

What it does *not* give you:

- Photos are **sent to the Space to be processed**. The server does not store them, but they do leave your device. This project does not claim otherwise.
- The models do **not** run on your phone. The phone only runs the page.
- It is **not offline**. You need a connection to reach the Space.

---

## Architecture

```
Phone or laptop browser
  - static/index.html (the UI)
  - IndexedDB (albums, cutouts, stories)
        |  HTTPS
        v
Hugging Face Space (Docker, free CPU)
  FastAPI app
    |-- rembg                  cutouts
    |-- small vision model     labels
    |-- small language model   stories, challenge prompts
    '-- small image model      story covers

Model weights come from the Hugging Face Hub.
```

The server is **stateless**. A free Space has no permanent disk, so nothing is saved there. The browser keeps the albums.

See `docs/diagrams.md` for the diagrams.

### API

| Method and path | Input | Output |
|---|---|---|
| `POST /api/cutout` | image file | PNG with transparent background |
| `POST /api/label` | image file | `{ "label": "...", "description": "..." }` |
| `POST /api/story` | `{ items, theme, place }` | `{ "title": "...", "text": "..." }` |
| `GET /api/challenge` | optional `time_of_day`, `count` | `{ "prompt": "..." }` |
| `POST /api/cover` | `{ title, theme, place, labels }` | PNG image |
| `GET /api/health` | none | `{ "status": "ok" }` |

The frontend calls `/api/cutout` and `/api/label` in parallel for each photo. `/api/cover` takes text only (no photos) and builds the image prompt on the server.

### Browser storage format (IndexedDB)

One `trips` store. Each record:

```json
{
  "id": "2026-10-06-walk-home",
  "name": "Walk home from college",
  "date": "2026-10-06",
  "place": "the old bridge",
  "items": [
    {
      "id": "a1",
      "cutout": "<Blob, transparent PNG>",
      "label": "Crumpled red leaf",
      "description": "spotted, slightly menacing",
      "note": "Fell right in front of me outside the library.",
      "tilt": -6
    }
  ],
  "stories": [
    { "id": "s1", "title": "The Case of the Smug Acorn", "theme": "mystery", "text": "...", "cover": "<Blob, PNG, optional>" }
  ]
}
```

`localStorage` is used only for the chosen theme. Clearing browser data deletes albums, so an export feature is on the roadmap.

---

## Project structure

```
wayside/
  README.md              # also the Hugging Face Space config (YAML header above)
  AGENT.md               # instructions for AI coding tools
  LICENSE                # choose one before publishing
  .gitignore
  Dockerfile
  requirements.txt
  docs/
    diagrams.md
    screenshots/         # for the DEV post
  app/                   # backend
    __init__.py
    main.py              # FastAPI app, routes, serves static/
    config.py            # model names, size limits, from env vars
    limits.py            # upload checks, rate limit, one-model-job-at-a-time lock
    services/
      __init__.py
      cutout.py          # rembg
      vision.py          # vision model, returns label JSON
      story.py           # story and challenge prompts
      cover.py           # text-to-image cover
  static/                # frontend, plain ES modules, no build step
    index.html           # shell only: markup, links to css and js
    css/
      themes.css         # the six theme variable blocks
      app.css            # layout, components, responsive rules
    js/
      main.js            # entry: wires navigation, starts the intro
      router.js          # which screen and page is showing
      state.js           # app state and small helpers
      data.js            # canned prompts, story themes, demo walks
      api.js             # every call to the AI: mock now, real fetch later
      storage.js         # IndexedDB for albums (not wired in yet)
      themes.js          # theme list and apply
      icons.js           # inline SVG icons
      art.js             # sample specimen drawings and logo
      cover.js           # cover prompt, HTML, canvas stand-in painter
      voice.js           # listen, pause, resume, stop
      components.js      # specimen boxes and bottom sheets
      views/
        intro.js         # loading screen and landing page
        collect.js       # collect page
        albums.js        # albums list
        trip.js          # a walk: grid, story builder, vault, covers
        stories.js       # all stories
        settings.js      # theme picker and model status
```

**Built so far:** everything under `static/`, plus `docs/` and `.gitignore`. **Not built yet:** `Dockerfile`, `requirements.txt` and the whole `app/` backend.

Frontend rules of thumb: all network calls live in `api.js`, all albums storage lives in `storage.js`, and views only render into `#app`.

---

## Deployment Guide

### Option 1: Hugging Face Spaces (Recommended for full local models)
- Hardware: Free CPU (2 vCPU, 16 GB RAM).
- Setup: Create Space, SDK Docker, Port 7860.
- All models (`rembg u2netp`, `SmolVLM-256M-Instruct`, `Qwen2.5-0.5B-Instruct`) run locally in-memory without exceeding RAM limits.

### Option 2: Render Free Tier (512 MB RAM limit)
- Hardware: Free Web Service (0.1 vCPU, 512 MB RAM, port 10000).
- `rembg` (u2netp) runs locally within ~40-60 MB RAM.
- Because local LLMs require >800 MB RAM and would trigger Render's 512 MB OOM-killer, use the **Provider Abstraction** with external open-model inference APIs:
  ```bash
  # In Render Environment Variables:
  WAYSIDE_VISION_PROVIDER=hf
  WAYSIDE_STORY_PROVIDER=hf
  HF_TOKEN=hf_...                # Free Hugging Face User Access Token
  ```
  Or connect to any OpenAI-compatible endpoint (Groq, Together, Ollama, OpenRouter):
  ```bash
  WAYSIDE_VISION_PROVIDER=openai
  WAYSIDE_STORY_PROVIDER=openai
  OPENAI_API_BASE=https://api.groq.com/openai/v1
  OPENAI_API_KEY=gsk_...
  ```

### Configuration Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WAYSIDE_VISION_PROVIDER` | `local` | `local`, `hf`, `openai`, `fallback` |
| `WAYSIDE_STORY_PROVIDER` | `local` | `local`, `hf`, `openai`, `fallback` |
| `WAYSIDE_VISION_MODEL` | `HuggingFaceTB/SmolVLM-256M-Instruct` | Vision model ID |
| `WAYSIDE_STORY_MODEL` | `Qwen/Qwen2.5-0.5B-Instruct` | Language model ID |
| `HF_TOKEN` | `""` | Hugging Face API token for serverless inference |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | Base URL for OpenAI-compatible inference |
| `OPENAI_API_KEY` | `""` | API key for OpenAI-compatible endpoint |
| `MAX_UPLOAD_MB` | `8` | Maximum image upload size in MB |
| `RATE_LIMIT_PER_MIN` | `30` | Per-IP rate limit per minute |
| `PORT` | `7860` | Web server port (automatically handles 10000 on Render) |

---

## Known limits

- **Free CPU is slow.** Expect a few seconds for a cutout and roughly 10 to 30 seconds for a story when running full local models.
- **Render 512 MB Free Tier:** Cannot host full local LLM weights without OOM; use `hf` or `openai` provider modes.
- **The Space/Render container sleeps** when idle, so the first visit after a quiet period takes a moment to wake.
- **Concurrency isolation:** Separate asyncio locks are maintained for `/api/cutout`, `/api/label`, and `/api/story`, allowing the frontend's parallel `Promise.all` requests to execute concurrently without contention.
- **Defensive fallbacks:** If any model call fails or times out, safe fallbacks are returned, preventing uncaught 500 errors in user experience.
- **Albums live in one browser.** Saved in IndexedDB on the device.

---

## Roadmap

**Core (do first)**
- [ ] Deploy a hello-world Space that serves the frontend and passes `/api/health`
- [ ] `/api/cutout` with rembg, wired to the shutter
- [ ] `/api/label` with a vision model returning clean JSON
- [ ] `/api/story` from labels, notes, theme and place
- [ ] Save and load walks in IndexedDB

**Next**
- [ ] `/api/cover` with a small text-to-image model, wired to the Make cover button
- [ ] `/api/challenge` that uses time of day and what you have collected
- [ ] Export and import an album as a file
- [ ] Open text-to-speech (Piper or Kokoro) instead of the browser voice

**Future**
- [ ] Several objects from one photo (detection and segmentation)
- [ ] Condition the cover on the actual specimens (img2img or IP-Adapter)
- [ ] Video generation for stories
- [ ] Run lighter models fully in the browser

---

## Challenge notes

- Built during the challenge window, one submission.
- The open models are load-bearing: remove them and the app stops working.
- The DEV post should include a demo, an honest "why open mattered" section, and what went wrong along the way.
- Submissions close October 11, 2026, 11:59 PM PDT. Check the official page for the rules, including whether a live link is required and the rules on using AI tools.

## License

MIT, to be confirmed before publishing.
