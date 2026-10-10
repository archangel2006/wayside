import os

WAYSIDE_VISION_PROVIDER = os.getenv("WAYSIDE_VISION_PROVIDER", "local").lower()
WAYSIDE_STORY_PROVIDER = os.getenv("WAYSIDE_STORY_PROVIDER", "local").lower()

WAYSIDE_VISION_MODEL = os.getenv("WAYSIDE_VISION_MODEL", "HuggingFaceTB/SmolVLM-256M-Instruct")
WAYSIDE_STORY_MODEL = os.getenv("WAYSIDE_STORY_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY", "")
HF_API_BASE = os.getenv("HF_API_BASE", "https://router.huggingface.co/hf-inference/models")

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "8"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
MODEL_TIMEOUT_SEC = int(os.getenv("MODEL_TIMEOUT_SEC", "90"))
PORT = int(os.getenv("PORT", "7860"))
