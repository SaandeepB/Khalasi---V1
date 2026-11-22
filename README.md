# Khalasi

A voice-first safety companion for Indian long-haul truck drivers on night runs. The product is a phone call: a Sarvam voice agent talks with the driver in his own language, notices sleepiness, and gets him to stop somewhere safe. If he goes silent while moving, it nudges, calls back, then alerts his family. The decision logic is plain, tested code.

Read `docs/MASTER_PROMPT.md` first; `CLAUDE.md` points every agent session at it.

## New teammate in 10 steps

1. Clone the repo and open it in Conductor (or any terminal). Conductor runs `scripts/conductor-setup.sh` for you; otherwise run it yourself.
2. Copy `.env.example` to `.env` and fill in the Sarvam keys and phone numbers. Never commit `.env`.
3. Backend: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. Tests: `cd backend && .venv/bin/python -m pytest -q`. All scenario tests from master prompt section 7 must pass.
5. Web: `cd web && npm install`.
6. Run both: `bash scripts/dev.sh`. Backend on port 8000 (or `$CONDUCTOR_PORT`), web on the next port. Open `/demo`.
7. MCP servers: `.mcp.json` registers Figr and the two Sarvam servers. In Claude Code run `/mcp`, authenticate `figr` (read access only) and `sarvam-voice-agents` (Sarvam SSO, once a day).
8. Designs: Figr project `khalasi`; a verbatim export sits in `design/figr-export/`. Map every screen in `docs/design-map.md`.
9. Live calls: create the agents per `docs/sarvam-setup.md`, expose the backend over HTTPS, set `PUBLIC_BASE_URL`, put teammates' numbers in `ALLOWED_NUMBERS`, and only then set `CALLS_ENABLED=true`.
10. Demo: follow `docs/demo-runbook.md`. Virtual mode needs no calls.

## Layout

```
backend/app/   FastAPI, pure decision engine, scheduler, Sarvam client, truck simulator
backend/tests/ scenario tests
web/           React + Vite + Tailwind v4, demo console and alert page (from Figr tokens)
agents/        Khalasi and Khalasi Alert instructions (paste verbatim into Sarvam)
design/        verbatim Figr exports
docs/          master prompt, architecture, open questions, Sarvam setup, design map, demo runbook
scripts/       Conductor setup, dev, test
```

## Rules in one breath

Safety logic is plain code. Fail safe. Never invent places. Driver-first privacy. No secrets in git. Don't guess Sarvam APIs. Calls are dangerous to test. Label simulated data. Hindi first. Figr sets the look.
