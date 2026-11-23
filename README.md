# Khalasi

A voice-first safety companion for Indian long-haul truck drivers on night runs. The product is a phone call: a Sarvam voice agent talks with the driver in his own language, notices sleepiness, and gets him to stop somewhere safe. If he goes silent while moving, it nudges, calls back, then alerts his family. The decision logic is plain, tested code.

Read `docs/MASTER_PROMPT.md` first; `CLAUDE.md` points every agent session at it.

**Branch `v2`:** this branch carries the v2 master prompt (games in calls, Ustaad points, memory with consent, check-ins by risk). Phase 2 work has not started yet; `main` is the v1 demo that Vercel deploys. Start Phase 2 with "Do Workstream 1 (v2 scope) from docs/MASTER_PROMPT.md (section 11, Phase 2)".

## New teammate in 10 steps

1. Clone the repo and open it in Conductor (or any terminal). Conductor runs `scripts/conductor-setup.sh` for you; otherwise run it yourself.
2. Copy `.env.example` to `.env` and fill in the Sarvam keys and phone numbers. Never commit `.env`.
3. Backend: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. Tests: `cd backend && .venv/bin/python -m pytest -q`. 62 tests, including all 29 scenarios from master prompt section 7, must pass. Persona evals offline: `backend/.venv/bin/python evals/run_personas.py --fake`.
5. Web: `cd web && npm install`.
6. Run both: `bash scripts/dev.sh`. Backend on port 8000 (or `$CONDUCTOR_PORT`), web on the next port. Routes: `/demo` console, `/a/demo` alert page, `/ops` night operations, `/pilot` pilot results, `/setup` driver setup, `/home` parked home.
7. MCP servers: `.mcp.json` registers Figr and the two Sarvam servers. In Claude Code run `/mcp`, authenticate `figr` (read access only) and `sarvam-voice-agents` (Sarvam SSO, once a day).
8. Designs: Figr project `khalasi`; a verbatim export sits in `design/figr-export/`. Map every screen in `docs/design-map.md`.
9. Live calls: create the agents per `docs/sarvam-setup.md`, expose the backend over HTTPS, set `PUBLIC_BASE_URL`, put teammates' numbers in `ALLOWED_NUMBERS`, and only then set `CALLS_ENABLED=true`.
10. Demo: follow `docs/demo-runbook.md`. Virtual mode needs no calls.

## Layout

```
backend/app/   FastAPI, pure decision engine, scheduler, Sarvam client, truck simulator
backend/tests/ scenario tests
web/           React + Vite + Tailwind v4: demo console (Figr), alert page, night ops, pilot, setup, home
evals/         persona eval harness and rubric judge (offline with --fake)
agents/        Khalasi and Khalasi Alert instructions (paste verbatim into Sarvam)
design/        verbatim Figr exports
docs/          master prompt, architecture, open questions, Sarvam setup, design map, demo runbook
scripts/       Conductor setup, dev, test
```

## Rules in one breath

Safety logic is plain code. Fail safe. Never invent places. Driver-first privacy. No secrets in git. Don't guess Sarvam APIs. Calls are dangerous to test. Label simulated data. Hindi first. Figr sets the look.

## Deploy the console to Vercel

Live demo: https://khalasi-saandeepboda99-6390.vercel.app/demo (alert page: https://khalasi-saandeepboda99-6390.vercel.app/a/demo?reason=unreachable). Deployed 2026-11-22 from `main`; every push to `main` redeploys.

The demo console and alert page are a static Vite build with no backend dependency in Virtual mode, so they deploy to Vercel as-is. The backend (timers, SSE, webhooks) is not a serverless fit; run it on Render, Fly or Railway and set `PUBLIC_BASE_URL` there.

1. In Vercel, import this repository. No environment variables are needed for Virtual mode.
2. Either leave Root Directory at the repo root (the root `vercel.json` installs and builds in `web/` and serves `web/dist`), or set Root Directory to `web` (Vercel detects Vite; `web/vercel.json` adds the SPA rewrite). Node 22 is required (`web/package.json` engines).
3. Deploy. Check `https://<project>.vercel.app/demo`, `/demo?figr_screen=scr_demo_alert` and `/a/demo?reason=unreachable`.
4. For the demo phone, open `https://<project>.vercel.app/a/demo?reason=not_answering&tel=+91XXXXXXXXXX` with the number of the teammate playing Raju. The `tel` query is demo-only and never stored.
