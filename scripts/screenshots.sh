#!/usr/bin/env bash
# Screenshot every built screen for docs/design-map.md and the slides.
# Usage: bash scripts/screenshots.sh [base_url]   (default http://localhost:5173)
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${1:-http://localhost:5173}"
OUT="docs/screenshots"
mkdir -p "$OUT"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
[ -x "$CHROME" ] || { echo "Chrome not found at $CHROME; set CHROME=/path/to/chrome"; exit 1; }

shot() { # name url width height
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-first-run --no-default-browser-check \
    --virtual-time-budget=4000 --window-size="$3,$4" --screenshot="$OUT/$1.png" "$2" >/dev/null 2>&1
  echo "wrote $OUT/$1.png"
}

shot demo-ready            "$BASE/demo"                                   1600 1000
shot demo-sleep-warning    "$BASE/demo?figr_screen=scr_demo_sleep"        1600 1000
shot demo-dark-stretch     "$BASE/demo?figr_screen=scr_demo_dark"         1600 1000
shot demo-sunita-alerted   "$BASE/demo?figr_screen=scr_demo_alert"        1600 1000
shot demo-unreachable      "$BASE/demo?figr_screen=scr_demo_unreachable"  1600 1000
shot alert-not-answering   "$BASE/a/demo?reason=not_answering"            500  1000
shot alert-unreachable     "$BASE/a/demo?reason=unreachable"              500  1000
