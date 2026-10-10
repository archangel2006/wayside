import gc
import io
from PIL import Image
import rembg

_cutout_session = None

def get_cutout_session():
    """Lazily load and cache the rembg u2netp session (4.7MB lightweight model for 512MB RAM)."""
    global _cutout_session
    if _cutout_session is None:
        _cutout_session = rembg.new_session("u2netp")
    return _cutout_session

def remove_background(image: Image.Image) -> bytes:
    """
    Downscales images larger than 800px longest side,
    strips background using lightweight u2netp, and returns PNG bytes.
    Frees memory buffers immediately with gc.collect().
    """
    max_dim = max(image.size)
    if max_dim > 800:
        scale = 800.0 / max_dim
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    session = get_cutout_session()
    result = rembg.remove(image, session=session)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    del result
    gc.collect()
    return buf.getvalue()
