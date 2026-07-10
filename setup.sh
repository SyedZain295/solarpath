#!/usr/bin/env bash
# Cross-platform dev setup (macOS / Linux / GitHub Codespaces)
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Solar Path dev setup"
python3 -m pip install --upgrade pip
pip install -r requirements-dev.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

pre-commit install || true
python scripts/validate_env.py
python scripts/ensure_ready.py

echo ""
echo "Done. Run: python app.py  or  docker compose up"
echo "Tests:  pytest tests/ -q --cov"
