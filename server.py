"""
server.py
=========
Pure-stdlib HTTP server that exposes the full StegaVault API.
No FastAPI / uvicorn / starlette required.

Endpoints mirror the original FastAPI design exactly so the frontend JS
(which uses fetch()) works without any changes.

Multipart parsing uses Python's email library (stdlib ≥ 3.6).
"""
from __future__ import annotations

import sys, os, io, json, base64, traceback, mimetypes, pathlib, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from email import policy as _epolicy
from email.parser import BytesParser as _BytesParser

# ── make backend importable ──────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

from backend.services import lsb_steganography as lsb
from backend.services import watermarking       as wm
from backend.services import tamper_detection   as td
from backend.utils    import logger
from backend.utils.file_utils  import validate_image_bytes, image_to_base64, make_thumbnail
from backend.utils.hashing     import hash_image_array, build_metadata
from PIL import Image
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# MULTIPART PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_multipart(body: bytes, content_type: str) -> dict:
    """
    Parse multipart/form-data body.
    Returns dict  {field_name: value}  where value is:
        - bytes  if it is a file upload   (has a filename)
        - str    for plain text fields
    Files also get a '_filename_<field>' key storing the original filename.
    """
    # email library needs the Content-Type header prepended
    full = b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body
    msg  = _BytesParser(policy=_epolicy.compat32).parsebytes(full)

    result: dict = {}
    payload = msg.get_payload()
    if not isinstance(payload, list):
        return result

    for part in payload:
        disp     = part.get("Content-Disposition", "")
        name     = _get_param(disp, "name")
        filename = _get_param(disp, "filename")
        data     = part.get_payload(decode=True)
        if data is None:
            data = b""
        if name is None:
            continue
        if filename:
            result[name] = data
            result[f"_filename_{name}"] = filename
        else:
            result[name] = data.decode("utf-8", errors="replace").strip()
    return result


def _get_param(header_value: str, param: str) -> str | None:
    """Extract a parameter value from a Content-Disposition header string."""
    m = re.search(rf'{param}="([^"]*)"', header_value)
    if m:
        return m.group(1)
    m = re.search(rf"{param}=([^;\\s]+)", header_value)
    return m.group(1) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# ALGORITHM REFERENCE DATA
# ─────────────────────────────────────────────────────────────────────────────

ALGORITHMS = {
    "LSB_Steganography": {
        "name": "Least Significant Bit (LSB)",
        "type": "Spatial domain steganography",
        "description": (
            "Replaces the lowest-order bit of each pixel channel with a payload bit. "
            "A ±1 change in a 0–255 value is imperceptible to humans. "
            "Capacity ≈ floor(W × H × 3 / 8) bytes. "
            "Output must be lossless PNG — JPEG recompression destroys embedded bits."
        ),
        "pros":  ["High capacity", "Visually imperceptible", "Fast"],
        "cons":  ["Fragile to JPEG re-compression", "Detectable by statistical steganalysis"],
        "use":   "Text-in-image, Image-in-image steganography",
    },
    "DCT_Watermarking": {
        "name": "Discrete Cosine Transform (DCT)",
        "type": "Frequency domain watermarking",
        "description": (
            "Divides the luminance channel into 8×8 blocks and applies the 2-D DCT. "
            "Watermark bits are embedded by quantising coefficient [4][5] to odd/even "
            "multiples of a 'strength' parameter. Mid-frequency coefficients are "
            "perceptually significant but partially survive JPEG compression."
        ),
        "pros":  ["Invisible to the eye", "Partially JPEG-resilient", "Blind extraction (no original needed)"],
        "cons":  ["Lower capacity than LSB", "Strength parameter must match for extraction"],
        "use":   "Invisible copyright watermarking",
    },
    "AES_256_GCM": {
        "name": "AES-256-GCM",
        "type": "Authenticated symmetric encryption",
        "description": (
            "Password → 256-bit key via PBKDF2-HMAC-SHA256 (200 000 iterations + random 16-byte salt). "
            "Payload encrypted with AES in Galois/Counter Mode using a random 96-bit nonce. "
            "GCM authentication tag detects any ciphertext tampering before decryption."
        ),
        "pros":  ["Strong 256-bit key", "Authenticated (detects tampering)", "Random nonce prevents replay attacks"],
        "cons":  ["Password must be remembered", "Wrong password raises an error before any data is returned"],
        "use":   "Password-protected steganography payloads",
    },
    "SHA_256_Hashing": {
        "name": "SHA-256",
        "type": "Cryptographic hash function",
        "description": (
            "Produces a 256-bit (64 hex char) digest of all pixel data. "
            "Even a single-bit pixel change completely changes the digest (avalanche effect). "
            "Comparing pre- and post-distribution digests detects any modification."
        ),
        "pros":  ["Collision-resistant", "Deterministic", "Fast"],
        "cons":  ["No secret key — anyone can recompute the hash of a modified image"],
        "use":   "Image integrity verification, tamper detection",
    },
    "Pixel_Diff_Heatmap": {
        "name": "Pixel-Difference Heatmap",
        "type": "Image forensics",
        "description": (
            "Computes the per-pixel max-channel absolute difference between original and suspect. "
            "Pixels above a configurable threshold are highlighted red; bounding boxes are drawn "
            "around clusters of changed pixels for easy visual inspection."
        ),
        "pros":  ["Visually intuitive", "Localises exactly which regions changed"],
        "cons":  ["Requires the original image for comparison"],
        "use":   "Tamper localisation and forensic comparison",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# HTTP HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class StegaVaultHandler(BaseHTTPRequestHandler):

    # ── silence default access log for cleanliness ───────────────────────────
    def log_message(self, fmt, *args):
        pass

    # ── route table ──────────────────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._serve_file(ROOT / "frontend" / "index.html", "text/html")
        elif path in ("/login", "/login.html"):
            self._serve_file(ROOT / "frontend" / "login.html", "text/html")
        elif path.startswith("/static/"):
            rel  = path[len("/static/"):]
            full = ROOT / "frontend" / rel
            mime = mimetypes.guess_type(str(full))[0] or "application/octet-stream"
            self._serve_file(full, mime)
        elif path == "/api/health":
            self._json({"status": "ok", "service": "StegaVault"})
        elif path == "/api/history":
            entries = logger.get_all()
            self._json({"success": True, "count": len(entries), "history": entries})
        elif path == "/api/algorithms":
            self._json({"algorithms": ALGORITHMS})
        elif path == "/docs":
            self._swagger_ui()
        elif path == "/openapi.json":
            self._json(self._openapi_spec())
        else:
            self._json({"error": "Not found"}, 404)

    def do_DELETE(self):
        if self.path == "/api/history":
            logger.clear()
            self._json({"success": True, "message": "History cleared."})
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b""
        ct     = self.headers.get("Content-Type", "")

        # Parse multipart
        fields: dict = {}
        if "multipart/form-data" in ct:
            try:
                fields = parse_multipart(body, ct)
            except Exception as e:
                self._json({"success": False, "detail": f"Multipart parse error: {e}"}, 400)
                return

        # ── Route ──────────────────────────────────────────────────────────
        try:
            if path == "/api/stego/encode-text":
                self._stego_encode_text(fields)
            elif path == "/api/stego/decode-text":
                self._stego_decode_text(fields)
            elif path == "/api/stego/encode-image":
                self._stego_encode_image(fields)
            elif path == "/api/stego/decode-image":
                self._stego_decode_image(fields)
            elif path == "/api/watermark/embed-dct":
                self._wm_embed_dct(fields)
            elif path == "/api/watermark/extract-dct":
                self._wm_extract_dct(fields)
            elif path == "/api/watermark/visible-text":
                self._wm_visible_text(fields)
            elif path == "/api/watermark/visible-image":
                self._wm_visible_image(fields)
            elif path == "/api/tamper/get-hash":
                self._tamper_get_hash(fields)
            elif path == "/api/tamper/verify-hash":
                self._tamper_verify_hash(fields)
            elif path == "/api/tamper/diff-heatmap":
                self._tamper_diff_heatmap(fields)
            elif path == "/api/tamper/lsb-noise":
                self._tamper_lsb_noise(fields)
            else:
                self._json({"error": "Endpoint not found"}, 404)
        except Exception as exc:
            traceback.print_exc()
            self._json({"success": False, "detail": str(exc)}, 500)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_file(self, path: pathlib.Path, mime: str):
        if not path.exists():
            self._json({"error": "Not found"}, 404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _require(self, fields: dict, *keys: str):
        for k in keys:
            if k not in fields:
                raise ValueError(f"Missing required field: '{k}'")

    def _img(self, fields: dict, key: str) -> bytes:
        """Get & validate image bytes from multipart field."""
        if key not in fields:
            raise ValueError(f"Missing image field: '{key}'")
        data = fields[key]
        fname = fields.get(f"_filename_{key}", "")
        validate_image_bytes(data, fname)
        return data

    def _field(self, fields: dict, key: str, default="") -> str:
        return str(fields.get(key, default)).strip()

    def _flt(self, fields: dict, key: str, default: float, mn: float, mx: float) -> float:
        try:
            v = float(fields.get(key, default))
        except (ValueError, TypeError):
            v = default
        return max(mn, min(mx, v))

    def _int(self, fields: dict, key: str, default: int, mn: int, mx: int) -> int:
        try:
            v = int(fields.get(key, default))
        except (ValueError, TypeError):
            v = default
        return max(mn, min(mx, v))

    def _err(self, msg: str, status: int = 422):
        self._json({"success": False, "detail": msg}, status)

    # ── STEGO endpoints ───────────────────────────────────────────────────────

    def _stego_encode_text(self, f):
        try:
            cover   = self._img(f, "cover_image")
            text    = self._field(f, "secret_text")
            pwd     = self._field(f, "password") or None
        except ValueError as e:
            self._err(str(e), 400); return
        if not text:
            self._err("secret_text is required.", 400); return
        if len(text) > 10000:
            self._err("secret_text exceeds 10 000 characters.", 400); return

        try:
            stego, meta = lsb.encode_text(cover, text, pwd)
        except ValueError as e:
            logger.record("text_encode_lsb", "error", f.get("_filename_cover_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("text_encode_lsb", "success", f.get("_filename_cover_image"), meta)
        self._json({
            "success":     True,
            "message":     "Text hidden successfully.",
            "stego_image": image_to_base64(stego),
            "thumbnail":   image_to_base64(make_thumbnail(stego)),
            "metadata":    meta,
        })

    def _stego_decode_text(self, f):
        try:
            stego = self._img(f, "stego_image")
            pwd   = self._field(f, "password") or None
        except ValueError as e:
            self._err(str(e), 400); return

        try:
            text, meta = lsb.decode_text(stego, pwd)
        except ValueError as e:
            logger.record("text_decode_lsb", "error", f.get("_filename_stego_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("text_decode_lsb", "success", f.get("_filename_stego_image"), meta)
        self._json({"success": True, "message": "Text extracted.",
                    "extracted_text": text, "metadata": meta})

    def _stego_encode_image(self, f):
        try:
            cover  = self._img(f, "cover_image")
            secret = self._img(f, "secret_image")
            pwd    = self._field(f, "password") or None
        except ValueError as e:
            self._err(str(e), 400); return

        try:
            stego, meta = lsb.encode_image(cover, secret, pwd)
        except ValueError as e:
            logger.record("image_encode_lsb", "error", f.get("_filename_cover_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("image_encode_lsb", "success", f.get("_filename_cover_image"), meta)
        self._json({
            "success":     True, "message": "Secret image hidden.",
            "stego_image": image_to_base64(stego),
            "thumbnail":   image_to_base64(make_thumbnail(stego)),
            "metadata":    meta,
        })

    def _stego_decode_image(self, f):
        try:
            stego = self._img(f, "stego_image")
            pwd   = self._field(f, "password") or None
        except ValueError as e:
            self._err(str(e), 400); return

        try:
            extracted, meta = lsb.decode_image(stego, pwd)
        except ValueError as e:
            logger.record("image_decode_lsb", "error", f.get("_filename_stego_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("image_decode_lsb", "success", f.get("_filename_stego_image"), meta)
        self._json({
            "success": True, "message": "Hidden image extracted.",
            "extracted_image": image_to_base64(extracted),
            "thumbnail": image_to_base64(make_thumbnail(extracted)),
            "metadata": meta,
        })

    # ── WATERMARK endpoints ───────────────────────────────────────────────────

    def _wm_embed_dct(self, f):
        try:
            img  = self._img(f, "image")
            text = self._field(f, "watermark_text")
            s    = self._flt(f, "strength", 25.0, 5.0, 60.0)
        except ValueError as e:
            self._err(str(e), 400); return
        if not text:
            self._err("watermark_text is required.", 400); return

        try:
            result, meta = wm.embed_dct_watermark(img, text, s)
        except ValueError as e:
            logger.record("dct_wm_embed", "error", f.get("_filename_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("dct_wm_embed", "success", f.get("_filename_image"), meta)
        self._json({
            "success": True, "message": "DCT watermark embedded.",
            "watermarked_image": image_to_base64(result),
            "thumbnail": image_to_base64(make_thumbnail(result)),
            "metadata": meta,
        })

    def _wm_extract_dct(self, f):
        try:
            img = self._img(f, "image")
            s   = self._flt(f, "strength", 25.0, 5.0, 60.0)
        except ValueError as e:
            self._err(str(e), 400); return

        try:
            text, meta = wm.extract_dct_watermark(img, s)
        except ValueError as e:
            logger.record("dct_wm_extract", "error", f.get("_filename_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("dct_wm_extract", "success", f.get("_filename_image"), meta)
        self._json({"success": True, "message": "DCT watermark extracted.",
                    "watermark_text": text, "metadata": meta})

    def _wm_visible_text(self, f):
        try:
            img   = self._img(f, "image")
            text  = self._field(f, "text")
            op    = self._int(f, "opacity",   128, 0, 255)
            pos   = self._field(f, "position", "bottom-right")
            fs    = self._int(f, "font_size",  36, 10, 120)
        except ValueError as e:
            self._err(str(e), 400); return
        if not text:
            self._err("text is required.", 400); return

        VALID_POS = {"center","top-left","top-right","bottom-left","bottom-right"}
        if pos not in VALID_POS:
            pos = "bottom-right"

        try:
            result, meta = wm.add_visible_watermark(img, text, op, pos, fs)
        except Exception as e:
            logger.record("visible_wm_text", "error", f.get("_filename_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("visible_wm_text", "success", f.get("_filename_image"), meta)
        self._json({
            "success": True, "message": "Visible text watermark applied.",
            "watermarked_image": image_to_base64(result),
            "thumbnail": image_to_base64(make_thumbnail(result)),
            "metadata": meta,
        })

    def _wm_visible_image(self, f):
        try:
            img    = self._img(f, "image")
            wm_img = self._img(f, "watermark_image")
            op     = self._flt(f, "opacity",  0.4,  0.0, 1.0)
            pos    = self._field(f, "position", "bottom-right")
            scale  = self._flt(f, "scale",    0.2,  0.05, 0.8)
        except ValueError as e:
            self._err(str(e), 400); return

        VALID_POS = {"center","top-left","top-right","bottom-left","bottom-right"}
        if pos not in VALID_POS:
            pos = "bottom-right"

        try:
            result, meta = wm.add_image_watermark(img, wm_img, op, pos, scale)
        except Exception as e:
            logger.record("visible_wm_image", "error", f.get("_filename_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("visible_wm_image", "success", f.get("_filename_image"), meta)
        self._json({
            "success": True, "message": "Image watermark applied.",
            "watermarked_image": image_to_base64(result),
            "thumbnail": image_to_base64(make_thumbnail(result)),
            "metadata": meta,
        })

    # ── TAMPER endpoints ──────────────────────────────────────────────────────

    def _tamper_get_hash(self, f):
        try:
            img = self._img(f, "image")
        except ValueError as e:
            self._err(str(e), 400); return

        arr  = np.array(Image.open(io.BytesIO(img)).convert("RGB"), dtype=np.uint8)
        h    = hash_image_array(arr)
        fname = f.get("_filename_image", "unknown")
        logger.record("get_hash", "success", fname, {"hash": h})
        self._json({
            "success":      True, "message": "Hash computed.",
            "sha256_hash":  h,
            "filename":     fname,
            "file_size_kb": round(len(img) / 1024, 2),
        })

    def _tamper_verify_hash(self, f):
        try:
            img  = self._img(f, "image")
            exph = self._field(f, "expected_hash")
        except ValueError as e:
            self._err(str(e), 400); return
        if len(exph) != 64:
            self._err("expected_hash must be exactly 64 hex characters.", 400); return

        result = td.verify_hash(img, exph)
        logger.record("verify_hash", "success", f.get("_filename_image"), result)
        self._json({"success": True, "message": result["verdict"], **result})

    def _tamper_diff_heatmap(self, f):
        try:
            orig = self._img(f, "original_image")
            susp = self._img(f, "suspect_image")
            thr  = self._int(f, "threshold", 10, 0, 100)
        except ValueError as e:
            self._err(str(e), 400); return

        try:
            heatmap, analysis = td.generate_diff_heatmap(orig, susp, thr)
        except Exception as e:
            logger.record("diff_heatmap", "error", f.get("_filename_original_image"), {"error": str(e)})
            self._err(str(e)); return

        logger.record("diff_heatmap", "success", f.get("_filename_original_image"), analysis)
        self._json({
            "success":       True,
            "message":       f"Analysis complete: {analysis['verdict']}",
            "heatmap_image": image_to_base64(heatmap),
            "analysis":      analysis,
        })

    def _tamper_lsb_noise(self, f):
        try:
            img = self._img(f, "image")
        except ValueError as e:
            self._err(str(e), 400); return

        result = td.check_lsb_noise(img)
        logger.record("lsb_noise", "success", f.get("_filename_image"), result)
        self._json({"success": True, "message": result["note"], **result})

    # ── Swagger UI ────────────────────────────────────────────────────────────

    def _swagger_ui(self):
        html = """<!DOCTYPE html>
<html><head><title>StegaVault API Docs</title>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" type="text/css"
  href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" >
</head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout",
    deepLinking: true
  })
</script>
</body></html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _openapi_spec(self) -> dict:
        return {
            "openapi": "3.0.0",
            "info": {"title": "StegaVault API", "version": "1.0.0",
                     "description": "Steganography, Watermarking & Tamper Detection API"},
            "paths": {
                "/api/stego/encode-text":     {"post": {"summary": "Hide text in image (LSB)", "tags": ["Steganography"]}},
                "/api/stego/decode-text":     {"post": {"summary": "Extract hidden text (LSB)", "tags": ["Steganography"]}},
                "/api/stego/encode-image":    {"post": {"summary": "Hide image in image (LSB)", "tags": ["Steganography"]}},
                "/api/stego/decode-image":    {"post": {"summary": "Extract hidden image (LSB)", "tags": ["Steganography"]}},
                "/api/watermark/embed-dct":   {"post": {"summary": "Embed invisible DCT watermark", "tags": ["Watermarking"]}},
                "/api/watermark/extract-dct": {"post": {"summary": "Extract DCT watermark", "tags": ["Watermarking"]}},
                "/api/watermark/visible-text":{"post": {"summary": "Add visible text watermark", "tags": ["Watermarking"]}},
                "/api/watermark/visible-image":{"post":{"summary": "Add logo watermark", "tags": ["Watermarking"]}},
                "/api/tamper/get-hash":        {"post": {"summary": "Get SHA-256 image hash", "tags": ["Tamper Detection"]}},
                "/api/tamper/verify-hash":     {"post": {"summary": "Verify image hash", "tags": ["Tamper Detection"]}},
                "/api/tamper/diff-heatmap":    {"post": {"summary": "Diff heatmap", "tags": ["Tamper Detection"]}},
                "/api/tamper/lsb-noise":       {"post": {"summary": "LSB noise analysis", "tags": ["Tamper Detection"]}},
                "/api/history":  {"get": {"summary": "Operation history", "tags": ["Utilities"]},
                                  "delete": {"summary": "Clear history", "tags": ["Utilities"]}},
                "/api/health":   {"get": {"summary": "Health check", "tags": ["Utilities"]}},
                "/api/algorithms":{"get": {"summary": "Algorithm reference", "tags": ["Utilities"]}},
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8000):
    # Ensure directories exist
    for d in ("uploads", "outputs", "logs"):
        (ROOT / d).mkdir(exist_ok=True)

    print(f"""
╔══════════════════════════════════════════════╗
║           StegaVault  is  running            ║
╠══════════════════════════════════════════════╣
║  Frontend  →  http://localhost:{port}           ║
║  API Docs  →  http://localhost:{port}/docs      ║
╚══════════════════════════════════════════════╝
""")
    server = HTTPServer((host, port), StegaVaultHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    run(host=host, port=port)
