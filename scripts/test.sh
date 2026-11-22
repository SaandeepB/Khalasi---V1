#!/usr/bin/env bash
# Run backend scenario tests and the web type-check/build.
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
if [ -d backend ]; then (cd backend && .venv/bin/python -m pytest -q) || status=1; fi
if [ -f web/package.json ]; then (cd web && npm run build) || status=1; fi
exit $status
