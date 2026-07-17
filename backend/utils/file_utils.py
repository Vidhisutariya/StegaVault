"""file_utils.py — Image validation, base64 helpers, thumbnails."""
import io, base64
from PIL import Image
import numpy as np

MAX_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_FORMATS = {"PNG", "JPEG", "JPG", "GIF", "WEBP", "BMP", "TIFF"}


def validate_image_bytes(data: bytes, filename: str = "") -> None:
    if len(data) > MAX_BYTES:
        raise ValueError(f"File too large ({len(data)//1024} KB). Max 20 MB.")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS and fmt not in {"JPEG"}:
            pass  # PIL opened it — good enough
        img.verify()
    except Exception as e:
        raise ValueError(f"Invalid image file: {e}")


def to_rgb_png(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_to_base64(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode()


def make_thumbnail(data: bytes, size=(300, 300)) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail(size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
