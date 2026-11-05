#!/usr/bin/env bash
# Setup för xray-detector (Linux-utveckling) med uv.
# På Windows: se README.md.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv saknas. Installera det först:"
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "==> Installerar beroenden i .venv med uv"
uv sync

echo "==> Skapar kataloger"
mkdir -p data/datasets models runs logs

echo "==> Klar. Starta med:"
echo "    uv run python main.py"
