"""
watermarking.py
===============
1. DCT invisible watermark  — embeds text in mid-frequency coefficients
2. Visible text watermark   — burned-in PIL text with shadow
3. Visible image watermark  — semi-transparent logo overlay

DCT Algorithm (per 8×8 luminance block):
  coeff[4][5] is quantised to multiples of `strength`.
  Even multiples → bit=0;  Odd multiples → bit=1.
  This is more robust than sign-based embedding.
"""
from __future__ import annotations
import io, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.fft import dctn, idctn          # scipy is available
from backend.utils.hashing import hash_image_array, build_metadata


# ── DCT helpers ───────────────────────────────────────────────────────────────

def _dct2(block: np.ndarray) -> np.ndarray:
    return dctn(block.astype(float), norm="ortho")


def _idct2(block: np.ndarray) -> np.ndarray:
    return idctn(block.astype(float), norm="ortho")


def _bits_from_text(text: str) -> list[int]:
    bits = []
    for ch in text:
        v = ord(ch)
        for s in range(7, -1, -1):
            bits.append((v >> s) & 1)
    return bits


def _text_from_bits(bits: list[int]) -> str:
    chars = []
    for i in range(0, len(bits) - len(bits) % 8, 8):
        v = 0
        for j in range(8):
            v = (v << 1) | bits[i + j]
        if v == 0:
            break
        chars.append(chr(v))
    return "".join(chars)


# ── DCT embed / extract ───────────────────────────────────────────────────────

def embed_dct_watermark(cover_bytes: bytes, watermark_text: str,
                        strength: float = 25.0) -> tuple[bytes, dict]:
    """Embed invisible watermark text using DCT on 8×8 luminance blocks."""
    orig_img  = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
    orig_hash = hash_image_array(np.array(orig_img))

    # Work in YCbCr luminance channel
    ycbcr = orig_img.convert("YCbCr")
    arr   = np.array(ycbcr, dtype=np.float64)
    Y     = arr[:, :, 0].copy()
    h, w  = Y.shape

    # Build bitstream: 16-bit length + data bits
    wm_bits    = _bits_from_text(watermark_text)
    n_bits     = len(wm_bits)
    len_bits   = [(n_bits >> (15 - i)) & 1 for i in range(16)]
    all_bits   = len_bits + wm_bits

    n_blocks_h = h // 8
    n_blocks_w = w // 8
    avail      = n_blocks_h * n_blocks_w

    if len(all_bits) > avail:
        raise ValueError(
            f"Watermark too long ({len(all_bits)} bits needed, "
            f"{avail} blocks available). Use fewer characters or a larger image.")

    bit_idx = 0
    for bi in range(n_blocks_h):
        for bj in range(n_blocks_w):
            if bit_idx >= len(all_bits):
                break
            r0, c0 = bi * 8, bj * 8
            block  = Y[r0:r0+8, c0:c0+8]
            D      = _dct2(block)
            # Quantise coeff[4][5]: even quant → 0, odd quant → 1
            q = round(D[4, 5] / strength)
            if all_bits[bit_idx] == 1:
                if q % 2 == 0:
                    q += 1          # make odd
            else:
                if q % 2 != 0:
                    q += 1          # make even
            D[4, 5]         = q * strength
            Y[r0:r0+8, c0:c0+8] = _idct2(D)
            bit_idx += 1

    arr[:, :, 0] = np.clip(Y, 0, 255)
    out_img = Image.fromarray(arr.astype(np.uint8), "YCbCr").convert("RGB")
    buf     = io.BytesIO()
    out_img.save(buf, format="PNG")
    meta    = build_metadata("dct_watermark_embed", orig_hash, {
        "watermark_text": watermark_text, "strength": strength,
        "bits_embedded": len(all_bits),
        "dimensions": f"{orig_img.width}x{orig_img.height}"})
    return buf.getvalue(), meta


def extract_dct_watermark(wm_bytes: bytes,
                          strength: float = 25.0) -> tuple[str, dict]:
    """Blind DCT watermark extraction — no original image needed."""
    img   = Image.open(io.BytesIO(wm_bytes)).convert("YCbCr")
    arr   = np.array(img, dtype=np.float64)
    Y     = arr[:, :, 0]
    h, w  = Y.shape
    nbh   = h // 8
    nbw   = w // 8

    ext_bits: list[int] = []
    for bi in range(nbh):
        for bj in range(nbw):
            r0, c0 = bi * 8, bj * 8
            D      = _dct2(Y[r0:r0+8, c0:c0+8])
            q      = round(D[4, 5] / strength)
            ext_bits.append(q % 2)      # odd → 1, even → 0

    if len(ext_bits) < 16:
        raise ValueError("Image too small to contain a DCT watermark.")

    # Read 16-bit length
    n_bits = 0
    for b in ext_bits[:16]:
        n_bits = (n_bits << 1) | b

    if n_bits <= 0 or n_bits > len(ext_bits) - 16:
        raise ValueError("No valid DCT watermark found (invalid length field).")

    text = _text_from_bits(ext_bits[16:16 + n_bits])
    return text, {"operation": "dct_watermark_extract",
                  "bits_read": n_bits, "watermark_text": text}


# ── Visible text watermark ────────────────────────────────────────────────────

def add_visible_watermark(image_bytes: bytes, text: str, opacity: int = 128,
                          position: str = "bottom-right",
                          font_size: int = 36) -> tuple[bytes, dict]:
    img     = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    font = _load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    iw, ih = img.size
    m = 20
    positions = {
        "center":       ((iw - tw) // 2,   (ih - th) // 2),
        "top-left":     (m,                 m),
        "top-right":    (iw - tw - m,       m),
        "bottom-left":  (m,                 ih - th - m),
        "bottom-right": (iw - tw - m,       ih - th - m),
    }
    x, y = positions.get(position, positions["bottom-right"])
    # Shadow
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, min(opacity, 200)))
    draw.text((x, y),         text, font=font, fill=(255, 255, 255, opacity))

    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf    = io.BytesIO()
    result.save(buf, format="PNG")
    meta = build_metadata("visible_watermark", "n/a", {
        "text": text, "opacity": opacity, "position": position})
    return buf.getvalue(), meta


def add_image_watermark(image_bytes: bytes, wm_bytes: bytes,
                        opacity: float = 0.4, position: str = "bottom-right",
                        scale: float = 0.2) -> tuple[bytes, dict]:
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    wm   = Image.open(io.BytesIO(wm_bytes)).convert("RGBA")

    nw = max(1, int(base.width * scale))
    nh = max(1, int(wm.height * (nw / wm.width)))
    wm = wm.resize((nw, nh), Image.LANCZOS)

    # Apply opacity to alpha channel
    r, g, b, a = wm.split()
    a = a.point(lambda p: int(p * opacity))
    wm.putalpha(a)

    iw, ih = base.size
    ww, wh = wm.size
    m = 15
    positions = {
        "center":       ((iw - ww) // 2,   (ih - wh) // 2),
        "top-left":     (m,                 m),
        "top-right":    (iw - ww - m,       m),
        "bottom-left":  (m,                 ih - wh - m),
        "bottom-right": (iw - ww - m,       ih - wh - m),
    }
    x, y    = positions.get(position, positions["bottom-right"])
    canvas  = Image.new("RGBA", base.size, (0, 0, 0, 0))
    canvas.paste(wm, (x, y), wm)
    result  = Image.alpha_composite(base, canvas).convert("RGB")

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    meta = build_metadata("image_watermark", "n/a", {
        "opacity": opacity, "position": position, "scale": scale})
    return buf.getvalue(), meta


# ── Font loader ───────────────────────────────────────────────────────────────

def _load_font(size: int):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()
