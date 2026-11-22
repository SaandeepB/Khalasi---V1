# Khalasi backend

Pure decision engine (`app/engine.py`) + thin FastAPI layer. Python 3.9+ (tested on 3.9.6).

1. `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. Tests (fully offline, no Sarvam calls): `.venv/bin/python -m pytest -q`
3. Copy `../.env.example` values into your shell or a `.env` loader; defaults are safe: `CALLS_ENABLED=false`, `DEMO_MODE=virtual`.
4. Seed demo data (optional, also done on startup): `.venv/bin/python -m app.seed`
5. Server: `.venv/bin/uvicorn app.main:app --port 8000` (from `backend/`)
6. Console stream: `curl -N localhost:8000/stream/console`; demo controls: `POST /demo/truck {"mode": "moving|stopped_dhaba|stopped_highway"}`, `POST /demo/event {"kind": "silence|no_answer|unreachable|dark_stretch|chup"}`
7. Tool endpoints need `Authorization: Bearer $TOOL_SECRET` when `TOOL_SECRET` is set.
8. Virtual mode logs every would-be call; only `DEMO_MODE=live` + `CALLS_ENABLED=true` + a number in `ALLOWED_NUMBERS` places a real call.
