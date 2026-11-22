#!/usr/bin/env bash
# List the Divyam model ids your key may use, to pick DIVYAM_MODEL. Reads .env; prints ids only, never the key.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
: "${DIVYAM_BASE_URL:?set DIVYAM_BASE_URL in .env}"
: "${DIVYAM_API_KEY:?set DIVYAM_API_KEY in .env}"
curl -sS --max-time 20 -H "Authorization: Bearer ${DIVYAM_API_KEY}" "${DIVYAM_BASE_URL%/}/models" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); items=d.get("data", d if isinstance(d, list) else []); print("\n".join(sorted(m.get("id", str(m)) for m in items)) or json.dumps(d)[:400])'
