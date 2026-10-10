import gc
import io
import logging
import time
from PIL import Image

logger = logging.getLogger("wayside.cutout")

_cutout_session = None

def get_cutout_session():
    """
    Lazily load and cache the rembg u2netp session.
    Using providers=['CPUExecutionProvider'] disables GPU device scanning.
    Lazy-loading ensures the server boots and binds port 10000 instantly (<1s).
    """
    global _cutout_session
    if _cutout_session is None:
        logger.info("[Session Init] Initializing rembg session for u2netp (CPUExecutionProvider)...")
        t0 = time.time()
        import rembg
        try:
            _cutout_session = rembg.new_session("u2netp", providers=["CPUExecutionProvider"])
            logger.info("[Session Init Success] rembg u2netp session loaded in %.2fs", time.time() - t0)
        except Exception as exc:
            logger.error("[Session Init Failed] Could not initialize rembg session: %s", exc, exc_info=True)
            raise
    return _cutout_session

def remove_background(image: Image.Image) -> bytes:
    """
    Downscales images larger than 800px longest side,
    strips background using lightweight u2netp, and returns PNG bytes.
    Frees memory buffers immediately with gc.collect().
    """
    import rembg

    original_size = image.size
    max_dim = max(image.size)
    if max_dim > 800:
        scale = 800.0 / max_dim
        new_size = (int(image.width * scale), int(image.height * scale))
        logger.info("[Cutout Preprocess] Downscaling image from %s to %s", original_size, new_size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        logger.info("[Cutout Preprocess] Image size %s within 800px threshold", original_size)

    session = get_cutout_session()

    logger.info("[Cutout Inference] Running rembg.remove()...")
    t0 = time.time()
    try:
        result = rembg.remove(image, session=session)
        logger.info("[Cutout Inference Success] rembg.remove() completed in %.2fs", time.time() - t0)
    except Exception as exc:
        logger.error("[Cutout Inference Failed] Error during rembg.remove(): %s", exc, exc_info=True)
        raise

    logger.info("[Cutout Encode] Encoding result as transparent PNG...")
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    logger.info("[Cutout Encode Success] Output PNG size: %d bytes", len(png_bytes))

    del result
    gc.collect()
    return png_bytes
