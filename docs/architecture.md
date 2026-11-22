# Architecture

```
Driver's phone ──call──▶ Sarvam "Khalasi" agent ──API tools──▶ Backend (FastAPI)
                              │                                  │
                              └──call-result webhook────────────▶│── Decision engine (pure)
                                                                 │── Scheduler (SQLite timers)
Sunita / backup / fleet desk ◀──call── Sarvam "Khalasi Alert" ◀──┤── Outbound calls (guarded)
                                                                 │── SQLite
Web (React) ◀──────────────── SSE live events ───────────────────┘
```

Principles (master prompt section 2): the engine is plain, tested code; no LLM output can cancel a call-back or alert; stale GPS counts as moving; a call without a valid end state is an unexpected end; the agent names only stops returned by `truck_status`; fleets never see transcripts.

## Modules and status, 2026-11-22

| Path | Role | Status |
|---|---|---|
| `backend/app/engine.py` | `decide(state, event, now) -> (new_state, actions)`, rules R1 to R16 | Built; 35 tests pass covering all 29 scenarios (`backend/tests/`) |
| `backend/app/config.py` | Default timings and env settings | Built |
| `backend/app/scheduler.py` | Timers persisted in SQLite, reloaded on start | Built, minimal |
| `backend/app/sarvam.py` | Outbound client with kill switch, allowlist, 12/hour cap; webhook parsing | Built, no live calls yet |
| `backend/app/sim.py` | Truck simulator: Nagpur → Jhansi, demo stops, two demo dark stretches | Built |
| `backend/app/main.py` | Tool endpoints, hooks, webhooks, SSE, demo controls | Built, virtual mode only; Python 3.9-compatible, stdlib sqlite3 + asyncio instead of SQLModel + APScheduler |
| `backend/app/llm.py` | Divyam wrapper, offline only | Not started (WS5) |
| `web/` | Demo console (Figr) in Virtual mode, alert page | Built |
| `agents/` | Agent instructions, Appendix A and B verbatim | Done |
| `evals/` | Persona harness | Not started (WS5) |

Live mode (real Sarvam calls) needs: both agents created in Sarvam (`docs/sarvam-setup.md`), a public HTTPS URL for tools and webhooks, and `CALLS_ENABLED=true` with teammates' numbers in `ALLOWED_NUMBERS`.

## Deployment

- **Web (Vercel):** static Vite build of `web/`; `vercel.json` at the root builds in `web/` and serves `web/dist` with an SPA rewrite, and `web/vercel.json` covers a Root Directory of `web`. Virtual mode needs no environment variables. The alert page is reachable at `/a/<token>` on the same host.
- **Backend (not Vercel):** FastAPI with persistent timers and SSE needs a long-running process: Render, Fly or Railway, or a cloudflared tunnel during development. Sarvam must reach `PUBLIC_BASE_URL` for tools and webhooks. Only one deployment at a time should be wired to Sarvam.
- **Live mode later:** point the web app at the backend with `VITE_API_BASE` (set by `scripts/dev.sh` locally) once the console consumes the SSE stream.
