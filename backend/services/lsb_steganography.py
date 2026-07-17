"""
lsb_steganography.py
====================
LSB (Least Significant Bit) steganography for text and image payloads.

Encoding:
  1. Build payload bytes (optionally AES-256-GCM encrypted).
  2. Prepend 4-byte big-endian length header.
  3. For each bit in the bitstream, replace the LSB of consecutive
     pixel channel bytes with that bit.

Decoding:
  1. Read 32 LSBs → payload length.
  2. Read (length × 8) more LSBs → payload bytes.
  3. Decrypt if password given.

Capacity = floor(W × H × 3 / 8) − 4 bytes.
Output is always lossless PNG (JPEG would destroy embedded LSBs).
"""
from __future__ import annotations
import io, numpy as np
from PIL import Image
from backend.utils.encryption import encrypt_data, decrypt_data
from backend.utils.hashing import hash_image_array, build_metadata


# ── bit helpers ──────────────────────────────────────────────────────────────

def _to_bits(data: bytes) -> list[int]:
    out = []
    for b in data:
        for s in range(7, -1, -1):
            out.append((b >> s) & 1)
    return out


def _from_bits(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - len(bits) % 8, 8):
        v = 0
        for j in range(8):
            v = (v << 1) | bits[i + j]
        out.append(v)
    return bytes(out)


def _capacity(arr: np.ndarray) -> int:
    h, w = arr.shape[:2]
    ch   = arr.shape[2] if arr.ndim == 3 else 1
    return (h * w * ch) // 8 - 4


# ── encode helpers ────────────────────────────────────────────────────────────

def _embed(arr: np.ndarray, payload: bytes) -> np.ndarray:
    cap = _capacity(arr)
    if len(payload) > cap:
        raise ValueError(
            f"Payload too large: {len(payload)} B > capacity {cap} B. "
            "Use a larger cover image or shorter message.")
    header = len(payload).to_bytes(4, "big")
    bits   = _to_bits(header + payload)
    flat   = arr.flatten().copy()
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit
    return flat.reshape(arr.shape)


def _extract(arr: np.ndarray) -> bytes:
    flat     = arr.flatten()
    len_bits = [int(flat[i] & 1) for i in range(32)]
    plen     = int.from_bytes(_from_bits(len_bits), "big")
    if plen <= 0 or plen > _capacity(arr):
        raise ValueError("No valid hidden data found in this image.")
    pbits    = [int(flat[32 + i] & 1) for i in range(plen * 8)]
    return _from_bits(pbits)


def _arr_to_png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), "RGB").save(buf, format="PNG")
    return buf.getvalue()


def _open_rgb(data: bytes) -> tuple[Image.Image, np.ndarray]:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return img, np.array(img, dtype=np.uint8)


# ── public API ────────────────────────────────────────────────────────────────

def encode_text(cover_bytes: bytes, secret_text: str,
                password: str | None = None) -> tuple[bytes, dict]:
    img, arr = _open_rgb(cover_bytes)
    orig_hash = hash_image_array(arr)
    payload   = secret_text.encode("utf-8")
    encrypted = False
    if password:
        payload   = encrypt_data(payload, password)
        encrypted = True
    stego_arr = _embed(arr, payload)
    meta = build_metadata("text_encode_lsb", orig_hash, {
        "payload_bytes": len(payload), "encrypted": encrypted,
        "dimensions": f"{img.width}x{img.height}"})
    return _arr_to_png(stego_arr), meta


def decode_text(stego_bytes: bytes,
                password: str | None = None) -> tuple[str, dict]:
    _, arr    = _open_rgb(stego_bytes)
    payload   = _extract(arr)
    if password:
        payload = decrypt_data(payload, password)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            "Extracted bytes are not valid UTF-8. "
            "Wrong password, or image was not encoded with this tool.")
    return text, {"operation": "text_decode_lsb", "length": len(text),
                  "password_used": bool(password)}


def encode_image(cover_bytes: bytes, secret_bytes: bytes,
                 password: str | None = None) -> tuple[bytes, dict]:
    cover_img, cover_arr = _open_rgb(cover_bytes)
    secret_img           = Image.open(io.BytesIO(secret_bytes)).convert("RGB")
    orig_hash            = hash_image_array(cover_arr)

    # Resize secret so it fits
    max_w = cover_img.width  // 2
    max_h = cover_img.height // 2
    secret_img.thumbnail((max_w, max_h), Image.LANCZOS)
    sbuf = io.BytesIO()
    secret_img.save(sbuf, format="PNG")
    payload   = sbuf.getvalue()
    encrypted = False
    if password:
        payload   = encrypt_data(payload, password)
        encrypted = True

    stego_arr = _embed(cover_arr, payload)
    meta = build_metadata("image_encode_lsb", orig_hash, {
        "payload_bytes": len(payload), "encrypted": encrypted,
        "secret_dims": f"{secret_img.width}x{secret_img.height}",
        "cover_dims":  f"{cover_img.width}x{cover_img.height}"})
    return _arr_to_png(stego_arr), meta


def decode_image(stego_bytes: bytes,
                 password: str | None = None) -> tuple[bytes, dict]:
    _, arr  = _open_rgb(stego_bytes)
    payload = _extract(arr)
    if password:
        payload = decrypt_data(payload, password)
    # Validate it is a real image
    try:
        test = Image.open(io.BytesIO(payload))
        fmt  = test.format
        test.close()
    except Exception:
        raise ValueError(
            "Extracted data is not a valid image. "
            "Wrong password or image not encoded with this tool.")
    return payload, {"operation": "image_decode_lsb",
                     "payload_bytes": len(payload),
                     "password_used": bool(password)}
