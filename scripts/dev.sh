#!/usr/bin/env bash
# Dev: backend on $CONDUCTOR_PORT (default 8000), web on the next port.
set -euo pipefail
cd "$(dirname "$0")/.."
BACKEND_PORT="${CONDUCTOR_PORT:-8000}"
WEB_PORT=$((BACKEND_PORT + 1))
export VITE_API_BASE="http://localhost:${BACKEND_PORT}"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

if [ -d backend ]; then
  (cd backend && set -a && [ -f ../.env ] && . ../.env; set +a; \
   .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT") &
fi
if [ -f web/package.json ]; then
  (cd web && npm run dev -- --port "$WEB_PORT" --strictPort) &
fi
echo "Backend: http://localhost:${BACKEND_PORT}   Web: http://localhost:${WEB_PORT}/demo"
wait
