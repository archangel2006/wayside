import os

WAYSIDE_VISION_MODEL = os.getenv("WAYSIDE_VISION_MODEL", "HuggingFaceTB/SmolVLM-256M-Instruct")
WAYSIDE_STORY_MODEL = os.getenv("WAYSIDE_STORY_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
WAYSIDE_IMAGE_MODEL = os.getenv("WAYSIDE_IMAGE_MODEL", "stabilityai/sd-turbo")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "8"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
MODEL_TIMEOUT_SEC = int(os.getenv("MODEL_TIMEOUT_SEC", "90"))
