"""
encryption.py  —  AES-256-GCM encrypt / decrypt.

Key derivation: PBKDF2-HMAC-SHA256 (200 000 iterations)
Wire format (base64-encoded blob):
    [16-byte salt][12-byte nonce][ciphertext + 16-byte GCM tag]
"""
import os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=200_000, backend=default_backend())
    return kdf.derive(password.encode())


def encrypt_data(plaintext: bytes, password: str) -> bytes:
    salt  = os.urandom(16)
    nonce = os.urandom(12)
    key   = _derive_key(password, salt)
    ct    = AESGCM(key).encrypt(nonce, plaintext, None)
    return base64.b64encode(salt + nonce + ct)


def decrypt_data(blob_b64: bytes, password: str) -> bytes:
    try:
        blob = base64.b64decode(blob_b64)
    except Exception:
        raise ValueError("Invalid encrypted payload.")
    if len(blob) < 44:
        raise ValueError("Payload too short.")
    salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
    key = _derive_key(password, salt)
    try:
        return AESGCM(key).decrypt(nonce, ct, None)
    except Exception:
        raise ValueError("Decryption failed — wrong password or tampered data.")
