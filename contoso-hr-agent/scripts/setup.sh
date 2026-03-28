#!/usr/bin/env bash
# Contoso HR Agent — Unix Setup
# Requires: Python 3.11+, uv (https://docs.astral.sh/uv/getting-started/installation/)
set -e

echo ""
echo "=== Contoso HR Agent Setup ==="

# Check uv
if ! command -v uv &>/dev/null; then
    echo "ERROR: 'uv' not found. Install from https://docs.astral.sh/uv/"
    exit 1
fi

# Create .env if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[!] Created .env from .env.example — edit it with your Azure AI Foundry credentials"
fi

# Create venv and sync
echo ""
echo "[1/4] Creating virtual environment..."
uv venv

echo ""
echo "[2/4] Installing dependencies..."
uv sync --all-extras

# Runtime directories
echo ""
echo "[3/4] Creating runtime directories..."
mkdir -p data/incoming data/processed data/knowledge data/chroma data/outgoing

# Seed knowledge base
echo ""
echo "[4/4] Seeding HR policy knowledge base..."
uv run hr-seed

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Edit .env with your Azure AI Foundry credentials"
echo "  2. Run: ./scripts/start.sh"
echo "  3. Open: http://localhost:8080/chat.html"
