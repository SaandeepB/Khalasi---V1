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
| `backend/app/engine.py` | `decide(state, event, now) -> (new_state, actions)`, rules R1 to R16 | See `backend/README.md` and test summary |
| `backend/app/config.py` | Default timings and env settings | Built |
| `backend/app/scheduler.py` | Timers persisted in SQLite, reloaded on start | Built, minimal |
| `backend/app/sarvam.py` | Outbound client with kill switch, allowlist, 12/hour cap; webhook parsing | Built, no live calls yet |
| `backend/app/sim.py` | Truck simulator: Nagpur → Jhansi, demo stops, two demo dark stretches | Built |
| `backend/app/main.py` | Tool endpoints, hooks, webhooks, SSE, demo controls | Built, virtual mode only |
| `backend/app/llm.py` | Divyam wrapper, offline only | Not started (WS5) |
| `web/` | Demo console (Figr) in Virtual mode, alert page | Built |
| `agents/` | Agent instructions, Appendix A and B verbatim | Done |
| `evals/` | Persona harness | Not started (WS5) |

Live mode (real Sarvam calls) needs: both agents created in Sarvam (`docs/sarvam-setup.md`), a public HTTPS URL for tools and webhooks, and `CALLS_ENABLED=true` with teammates' numbers in `ALLOWED_NUMBERS`.
