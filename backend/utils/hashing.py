"""
hashing.py  —  SHA-256 image hashing + tamper detection helpers.
"""
import hashlib, hmac as _hmac, json
from datetime import datetime, timezone
import numpy as np


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_image_array(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def compare_hashes(expected: str, current: str) -> dict:
    match = _hmac.compare_digest(expected, current)
    return {
        "match":          match,
        "hash_original":  expected,
        "hash_current":   current,
        "verdict":        "INTACT — hashes match." if match else "TAMPERED — hashes differ!",
    }


def build_metadata(operation: str, original_hash: str, extra: dict | None = None) -> dict:
    m = {"operation": operation, "original_hash": original_hash,
         "timestamp": datetime.now(timezone.utc).isoformat()}
    if extra:
        m.update(extra)
    return m
