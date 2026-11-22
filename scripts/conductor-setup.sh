#!/usr/bin/env bash
# Conductor setup: runs once per new workspace (non-interactive shell).
set -euo pipefail
cd "$(dirname "$0")/.."

# 1. Secrets: copy .env from the main checkout if this workspace has none.
if [ ! -f .env ] && [ -n "${CONDUCTOR_ROOT_PATH:-}" ] && [ -f "$CONDUCTOR_ROOT_PATH/.env" ]; then
  cp "$CONDUCTOR_ROOT_PATH/.env" .env
  echo "Copied .env from $CONDUCTOR_ROOT_PATH"
fi
[ -f .env ] || echo "No .env found. Copy .env.example to .env and fill it in."

# 2. Backend: newest Python available, venv, deps.
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -d backend ]; then
  "$PY" -m venv backend/.venv
  backend/.venv/bin/pip install --quiet --upgrade pip
  [ -f backend/requirements.txt ] && backend/.venv/bin/pip install --quiet -r backend/requirements.txt
fi

# 3. Web deps.
if [ -f web/package.json ]; then
  (cd web && npm install --no-audit --no-fund)
fi
echo "Setup done."
