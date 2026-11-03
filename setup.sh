#!/usr/bin/env bash
# Setup för xray-detector (Linux-utveckling).
# På Windows: se README.md (setup.ps1 / manuell installation).
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Skapar virtuellt miljö (venv)"
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installerar beroenden"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Skapar kataloger"
mkdir -p data/datasets models runs logs

echo "==> Klar. Starta med:"
echo "    source .venv/bin/activate"
echo "    python main.py"
