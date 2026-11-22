# Open questions

Rule 6: record anything unverified here before coding against it. Update the row when answered.

| # | Question (master prompt section 12) | Status, 2026-11-22 | Notes |
|---|---|---|---|
| 1 | Exact API-tool definition format; how tools read and write agent variables | Open | Check through the `sarvam-voice-agents` MCP or docs.sarvam.ai/voice-agents before WS2 wires tools. |
| 2 | Names of call-context variables available to tools and hooks | Open | Tools fall back to `trip_id` in every body. |
| 3 | Any live event or transcript stream during a call? | Open | Console assumes `report_signal` plus the post-call transcript. |
| 4 | Do nudges appear in `interaction_transcript`? | Open | `sarvam.py` has a helper for "ends in unanswered nudges"; verify the shape. |
| 5 | How nudge delays add up; total time to hang-up | Open | Target about 40 s of silence in total. |
| 6 | Webhook delivery latency; signing-secret format | Open | Measure on the first live call. |
| 7 | Network allowlisting for API tools | Open | |
| 8 | Divyam base URL, auth header, model names | Open | WS5 not started. |
| 9 | Outbound rate limits; ring time before `no_answer` | Open | Scenario tests assume a 25 s ring. |
| 10 | Can the agent end the call itself after a goodbye? | Open | If not, revisit the valid-end-state rule before the demo. |
| 11 | Can telephony report a missed call to a URL? | Open | `ENTRY_MODE=inbound` for the MVP. |
| 12 | Does the inbound webhook carry the same fields as outbound? | Open | |
| 13 | Figr: which project, which design is which screen | Answered | Project is `khalasi`. Only the Demo console exists, in five states. See `docs/design-map.md`. |
| 14 | Figr: React prototypes, design system attached? | Answered | React plus Tailwind v4 tokens. Verbatim export in `design/figr-export/khalasi/`. |

## Answered along the way

- The `sarvam-voice-agents` MCP accepts only OAuth 2.1 through Sarvam SSO (authorization code with PKCE). The API key is rejected under `X-API-Key`, `Authorization: Bearer` and `api-subscription-key`. The token lasts 24 hours with no refresh, so sign in daily with `/mcp` or `claude mcp login sarvam-voice-agents`.
- `sarvam-docs` MCP is public. Figr MCP is OAuth; the CLI requests `figr:read figr:write`, decline write when the consent page allows it.
- `SARVAM_API_KEY` is for the REST API (Instant Outbound) only and lives in the gitignored `.env`.
- This Mac has Python 3.9.6 only; the spec says 3.11+. The backend is written 3.9-compatible; deploy on 3.11+.
- Conductor: `.conductor/settings.toml` is used instead of the legacy `conductor.json`, because the Mac client ignores `conductor.json` once the TOML exists.
- Project-scope MCP servers need approval before `claude mcp login` works. `.claude/settings.json` approves them in trusted checkouts; a fresh Conductor worktree is untrusted, so the same allowlist also sits in the user's `~/.claude/settings.json`.

## Unverified assumptions in the backend (fix before Live mode)

- Webhook signature header name is assumed to be `X-Sarvam-Signature` with HMAC-SHA256 over the raw body; verification is skipped when `SARVAM_WEBHOOK_SECRET` is empty (open question 6).
- On-start hook caller field is guessed: the code tries `caller_number`, `from`, `user_phone_number`, `phone` (open question 2).
- Call end time is taken as webhook arrival time, so the 30 s valid-end window includes delivery latency (open question 6).
- Alert-page tokens are random and stored with a 24 h expiry in SQLite, not signed as section 6 says. Swap for a signed token before any public deployment of the backend.
- The alert-page link is pushed to the console stream only; SMS and the QR code are not built.
- `truck_status` uses wall-clock time, so outside night hours `time_now` and `minutes_since_last_rest` look odd; the web console runs its own simulated clock for the stage demo.

