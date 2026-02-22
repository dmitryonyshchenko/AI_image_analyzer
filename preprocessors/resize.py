"""
Preprocessor: Resize

Proportionally resizes images to fit within MAX_WIDTH × MAX_HEIGHT.
Smaller images are NOT upscaled — they are returned unchanged.
Uses LANCZOS resampling for best downscale quality.
"""
from PIL import Image

MAX_WIDTH  = 800
MAX_HEIGHT = 600


def process(image: Image.Image) -> Image.Image:
    """
    Return a proportionally resized copy if the image exceeds the size limit.
    If the image already fits, the original object is returned unchanged.
    """
    w, h = image.size
    if w <= MAX_WIDTH and h <= MAX_HEIGHT:
        return image  # already within limits — don't upscale

    ratio    = min(MAX_WIDTH / w, MAX_HEIGHT / h)
    new_size = (int(w * ratio), int(h * ratio))
    return image.resize(new_size, Image.LANCZOS)
