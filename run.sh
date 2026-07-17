#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# StegaVault — One-shot setup & launch
# Usage:  bash run.sh          (default port 8000)
#         bash run.sh 9000     (custom port)
# ─────────────────────────────────────────────────────────────────────────────
set -e
PORT=${1:-8000}
PYTHON=$(which python3 2>/dev/null || which python)

echo "╔═══════════════════════════════════════╗"
echo "║        StegaVault  Setup              ║"
echo "╚═══════════════════════════════════════╝"
echo "Python: $($PYTHON --version)"

# Virtual environment
if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment…"
  $PYTHON -m venv .venv
fi

# Activate
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true

# Install deps
echo "→ Installing dependencies (this may take a minute)…"
pip install -r requirements.txt -q

# Directories
mkdir -p uploads outputs logs

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║   Starting StegaVault on :$PORT         ║"
echo "╠═══════════════════════════════════════╣"
echo "║  Dashboard → http://localhost:$PORT    ║"
echo "║  API Docs  → http://localhost:$PORT/docs║"
echo "╚═══════════════════════════════════════╝"
echo ""

$PYTHON server.py $PORT
