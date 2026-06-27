"""Normalize PDF-extracted figures for CLIP / PIL (skip masks, JPX quirks, tiny tiles)."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from src.utils.logger import get_logger

logger = get_logger(__name__)

MIN_CLIP_EDGE_PX = 16
# Formats PyMuPDF may emit that often break CLIP unless re-encoded.
_REENCODE_EXTENSIONS = frozenset({".jpx", ".jp2", ".j2k", ".jxl", ".webp", ".tif", ".tiff"})


def load_rgb_image_for_clip(path: str | Path) -> Image.Image | None:
    """
    Load an image as a clean in-memory RGB PIL image suitable for CLIP.
    Returns None if the file is missing, too small, or not a usable raster figure.
    """
    path = Path(path)
    if not path.is_file():
        return None

    try:
        with Image.open(path) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened)

            if image.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                alpha = image.split()[-1] if image.mode in ("RGBA", "LA") else None
                rgb = image.convert("RGB")
                if alpha is not None:
                    background.paste(rgb, mask=alpha)
                    image = background
                else:
                    image = rgb
            elif image.mode != "RGB":
                image = image.convert("RGB")

            width, height = image.size
            if width < MIN_CLIP_EDGE_PX or height < MIN_CLIP_EDGE_PX:
                logger.debug("Skipping tiny image %s (%sx%s)", path.name, width, height)
                return None

            # Re-encode exotic PDF extractions so downstream CLIP never sees odd arrays.
            if path.suffix.lower() in _REENCODE_EXTENSIONS or _needs_reencode(image):
                return _jpeg_roundtrip(image)

            return image.copy()
    except (UnidentifiedImageError, OSError, ValueError, TypeError) as exc:
        logger.warning("Skipping unreadable image %s: %s", path, exc)
        return None


def _needs_reencode(image: Image.Image) -> bool:
    try:
        import numpy as np

        arr = np.asarray(image)
        if arr.ndim != 3 or arr.shape[2] not in (1, 3, 4):
            return True
        if arr.shape[0] < MIN_CLIP_EDGE_PX or arr.shape[1] < MIN_CLIP_EDGE_PX:
            return True
    except Exception:
        return True
    return False


def _jpeg_roundtrip(image: Image.Image) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    with Image.open(buffer) as normalized:
        return normalized.convert("RGB").copy()
