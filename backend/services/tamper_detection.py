"""
tamper_detection.py
===================
1. verify_hash      — SHA-256 comparison (any pixel change → mismatch)
2. generate_diff_heatmap — pixel-level diff with red highlight + bounding boxes
3. check_lsb_noise  — statistical LSB analysis (steganalysis heuristic)
"""
from __future__ import annotations
import io
import numpy as np
from PIL import Image, ImageDraw
from backend.utils.hashing import hash_image_array, compare_hashes


def verify_hash(image_bytes: bytes, expected_hash: str) -> dict:
    arr  = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"), dtype=np.uint8)
    curr = hash_image_array(arr)
    return compare_hashes(expected_hash, curr)


def generate_diff_heatmap(orig_bytes: bytes, suspect_bytes: bytes,
                          threshold: int = 10) -> tuple[bytes, dict]:
    orig_img    = Image.open(io.BytesIO(orig_bytes)).convert("RGB")
    susp_img    = Image.open(io.BytesIO(suspect_bytes)).convert("RGB")
    if susp_img.size != orig_img.size:
        susp_img = susp_img.resize(orig_img.size, Image.LANCZOS)

    orig_arr = np.array(orig_img, dtype=np.int16)
    susp_arr = np.array(susp_img, dtype=np.int16)
    diff     = np.abs(orig_arr - susp_arr).max(axis=2).astype(np.uint8)   # (H,W)
    mask     = (diff > threshold).astype(np.uint8)

    tampered = int(mask.sum())
    total    = int(mask.size)
    ratio    = round(tampered / total * 100, 4)

    # Build heatmap: amplify red in tampered regions
    heat = susp_arr.copy().astype(np.int16)
    amp  = np.clip(diff.astype(np.float32) * 4, 0, 255).astype(np.int16)
    heat[:, :, 0] = np.where(mask, np.clip(heat[:, :, 0] + amp, 0, 255), heat[:, :, 0])
    heat[:, :, 1] = np.where(mask, np.clip(heat[:, :, 1] - amp, 0, 255), heat[:, :, 1])
    heat[:, :, 2] = np.where(mask, np.clip(heat[:, :, 2] - amp, 0, 255), heat[:, :, 2])

    heat_img = Image.fromarray(heat.astype(np.uint8), "RGB")
    heat_img = _draw_boxes(heat_img, mask)

    buf = io.BytesIO()
    heat_img.save(buf, format="PNG")

    orig_hash = hash_image_array(np.array(orig_img, dtype=np.uint8))
    susp_hash = hash_image_array(np.array(susp_img, dtype=np.uint8))

    analysis = {
        "tampered":          tampered > 0,
        "verdict":           "TAMPERED" if tampered > 0 else "CLEAN",
        "tampered_pixels":   tampered,
        "total_pixels":      total,
        "tamper_ratio_pct":  ratio,
        "original_hash":     orig_hash,
        "suspect_hash":      susp_hash,
        "hashes_match":      orig_hash == susp_hash,
        "threshold":         threshold,
        "dimensions":        f"{orig_img.width}x{orig_img.height}",
    }
    return buf.getvalue(), analysis


def _draw_boxes(img: Image.Image, mask: np.ndarray) -> Image.Image:
    """Draw red bounding rectangles around clusters of tampered pixels."""
    draw = ImageDraw.Draw(img)
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return img

    def bands(idx, gap=8):
        result, s, e = [], idx[0], idx[0]
        for v in idx[1:]:
            if v - e <= gap:
                e = v
            else:
                result.append((s, e)); s = e = v
        result.append((s, e))
        return result

    for r0, r1 in bands(rows)[:20]:
        for c0, c1 in bands(cols)[:20]:
            if mask[r0:r1+1, c0:c1+1].any():
                draw.rectangle([c0-2, r0-2, c1+2, r1+2],
                               outline=(255, 0, 0), width=2)
    return img


def check_lsb_noise(image_bytes: bytes) -> dict:
    """Heuristic: uniform LSB distribution hints at embedded data."""
    arr   = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"), dtype=np.uint8)
    ratio = float((arr & 1).mean())
    dev   = abs(ratio - 0.5)
    # Very uniform (~0.50) → suspicious; natural images deviate more
    suspicious = dev < 0.01
    return {
        "lsb_ones_ratio":          round(ratio, 6),
        "deviation_from_natural":  round(dev, 6),
        "suspicious":              suspicious,
        "note": ("LSB distribution is suspiciously uniform — may contain embedded data."
                 if suspicious else "LSB distribution appears natural."),
    }
