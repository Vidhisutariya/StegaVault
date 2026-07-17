# ⬡ StegaVault — Steganography & Watermarking Platform

> A production-ready, full-stack steganography web application.
> **Pure Python stdlib server** (no FastAPI required) + HTML/CSS/JS frontend.
> AES-256-GCM encryption · DCT watermarking · SHA-256 tamper detection.

---

## � Team & Project Details

- **Project type:** 4th semester software group project
- **Institute:** Depstar
- **Team members:**
  - `Vidhisutariya` — `24DCE143`
  - `Priyanshi Bhatt` — `D25DCE166`

---

## �📁 Project Structure

```
stegavault/
│
├── server.py                      ← Pure stdlib HTTP server (entry point)
├── requirements.txt               ← pip dependencies
├── run.sh                         ← One-command setup & launch
│
├── backend/
│   ├── services/
│   │   ├── lsb_steganography.py   ← LSB encode/decode (text + image-in-image)
│   │   ├── watermarking.py        ← DCT invisible + visible watermarks
│   │   └── tamper_detection.py    ← Hash check + pixel-diff heatmap
│   └── utils/
│       ├── encryption.py          ← AES-256-GCM + PBKDF2 key derivation
│       ├── hashing.py             ← SHA-256 + compare helpers
│       ├── file_utils.py          ← Image validation + base64 helpers
│       └── logger.py              ← In-memory audit log (deque, 200 entries)
│
├── frontend/
│   ├── index.html                 ← Single-page application (14 panels)
│   ├── css/style.css              ← Full responsive dark/light stylesheet
│   └── js/app.js                  ← All frontend logic (vanilla JS)
│
├── uploads/                       ← Runtime upload temp directory
├── outputs/                       ← Generated output files
└── logs/                          ← Log directory
```

---

## 🚀 Quick Start

### Requirements
- Python 3.9+
- pip

### Option A — One command
```bash
git clone https://github.com/yourname/stegavault
cd stegavault
bash run.sh
```

### Option B — Manual
```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create directories
mkdir -p uploads outputs logs

# 4. Launch server
python3 server.py
```

### Access
| URL | Description |
|-----|-------------|
| http://localhost:8000 | Frontend Dashboard |
| http://localhost:8000/docs | Swagger UI (API reference) |

---

## ✅ Feature Checklist

### Steganography
- [x] **Text → Image** (LSB encoding, lossless PNG output)
- [x] **Extract Text** (LSB decoding with length-header protocol)
- [x] **Image → Image** (LSB, auto-resize, PNG serialisation)
- [x] **Extract Hidden Image**

### Watermarking
- [x] **Invisible DCT** (mid-frequency coefficient embedding, blind extraction)
- [x] **Visible Text** (PIL ImageDraw, shadow, opacity, position, font size)
- [x] **Logo / Image Overlay** (RGBA alpha compositing, scale, opacity)

### Security
- [x] **AES-256-GCM encryption** (PBKDF2-HMAC-SHA256 key derivation, random nonce)
- [x] **SHA-256 tamper detection** (pixel-data hashing)
- [x] **Pixel-diff heatmap** (red highlight + bounding boxes on tampered regions)
- [x] **LSB noise analysis** (statistical steganalysis heuristic)

### UX / System
- [x] **Dark / Light mode** toggle
- [x] **Drag-and-drop** file upload with preview
- [x] **Capacity bar** (real-time for text encoding)
- [x] **Operation audit log** (in-memory, 200 entries, clearable)
- [x] **Algorithm reference** panel (live from `/api/algorithms`)
- [x] **Swagger UI** at `/docs`
- [x] **Toast notifications** for every operation
- [x] **Loading overlay** during API calls

---

## 🔬 Algorithm Details

### 1. LSB Steganography

```
Pixel R=11001000  G=10110101  B=11001101
Payload bits:   1           0           1
Result:   R=11001001  G=10110100  B=11001101
               ↑ changed        ↑ changed
```

**Wire format:** `[4-byte big-endian length][payload bytes]`

Capacity ≈ `floor(W × H × 3 / 8) − 4` bytes.
Output is always lossless PNG — JPEG recompression destroys LSBs.

### 2. DCT Watermarking

For each 8×8 luminance block:
1. Apply 2-D DCT.
2. Take coefficient `[4][5]` (mid-frequency — invisible but non-trivial).
3. Quantise to multiples of `strength`:
   - Even multiple → bit = 0
   - Odd multiple  → bit = 1
4. Apply IDCT.

Extraction reads the sign/parity of `coeff[4][5]` — **no original needed**.

**Header:** 16-bit length prefix so the extractor knows how many bits to read.

### 3. AES-256-GCM Encryption

```
password ──PBKDF2-HMAC-SHA256 (200k iterations, random 16-byte salt)──▶ 256-bit key
random 96-bit nonce ──▶ AES-GCM encrypt ──▶ ciphertext + 16-byte auth tag
wire format: base64( salt[16] + nonce[12] + ciphertext + tag[16] )
```

Wrong password → `InvalidTag` exception (authentication failure before any bytes returned).

### 4. SHA-256 Tamper Detection

```
original pixels ──SHA-256──▶ digest_A  (store this)
suspect  pixels ──SHA-256──▶ digest_B

digest_A == digest_B → INTACT
digest_A != digest_B → TAMPERED  (even 1-bit change cascades via avalanche effect)
```

---

## 📡 API Reference

All `POST` endpoints accept `multipart/form-data`. All responses are JSON.

### Steganography
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/stego/encode-text`  | Hide text in image (LSB) |
| POST | `/api/stego/decode-text`  | Extract hidden text |
| POST | `/api/stego/encode-image` | Hide image in image |
| POST | `/api/stego/decode-image` | Extract hidden image |

### Watermarking
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/watermark/embed-dct`      | Embed invisible DCT watermark |
| POST | `/api/watermark/extract-dct`    | Extract DCT watermark |
| POST | `/api/watermark/visible-text`   | Add visible text watermark |
| POST | `/api/watermark/visible-image`  | Add logo watermark |

### Tamper Detection
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tamper/get-hash`    | Compute SHA-256 hash |
| POST | `/api/tamper/verify-hash` | Compare hash vs image |
| POST | `/api/tamper/diff-heatmap`| Generate tamper heatmap |
| POST | `/api/tamper/lsb-noise`   | LSB noise analysis |

### Utilities
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/history`    | Operation audit log |
| DELETE | `/api/history`    | Clear log |
| GET    | `/api/health`     | Health check |
| GET    | `/api/algorithms` | Algorithm reference JSON |
| GET    | `/docs`           | Swagger UI |

---

## 🌐 Deployment

### Render.com
```yaml
# render.yaml
services:
  - type: web
    name: stegavault
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python server.py $PORT
```

### Railway
```bash
railway login && railway init && railway up
```
Set env var: `PORT=8000`

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p uploads outputs logs
EXPOSE 8000
CMD ["python", "server.py", "8000"]
```
```bash
docker build -t stegavault . && docker run -p 8000:8000 stegavault
```

### VPS (Nginx + systemd)
```nginx
# /etc/nginx/sites-available/stegavault
server {
    listen 80; server_name yourdomain.com;
    client_max_body_size 25M;
    location / { proxy_pass http://127.0.0.1:8000; }
}
```
```ini
# /etc/systemd/system/stegavault.service
[Service]
WorkingDirectory=/var/www/stegavault
ExecStart=/var/www/stegavault/.venv/bin/python server.py 8000
Restart=always
```

---

## 🧪 Quick cURL Tests

```bash
# Health check
curl http://localhost:8000/api/health

# Encode text
curl -X POST http://localhost:8000/api/stego/encode-text \
  -F "cover_image=@photo.png" \
  -F "secret_text=Hello World" \
  -F "password=secret" | python3 -m json.tool

# Get hash
curl -X POST http://localhost:8000/api/tamper/get-hash \
  -F "image=@photo.png" | python3 -m json.tool
```

---

*StegaVault — second Year Engineering Project | DEPSTAR, CHARUSAT University*
