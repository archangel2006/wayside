import io
from PIL import Image
import rembg

_cutout_session = None

def get_cutout_session():
    """Lazily load and cache the rembg session singleton."""
    global _cutout_session
    if _cutout_session is None:
        _cutout_session = rembg.new_session("u2net")
    return _cutout_session

def remove_background(image: Image.Image) -> bytes:
    """
    Downscales images larger than 1024px longest side,
    strips background using rembg U2-Net, and returns PNG bytes.
    """
    max_dim = max(image.size)
    if max_dim > 1024:
        scale = 1024.0 / max_dim
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    session = get_cutout_session()
    result = rembg.remove(image, session=session)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
