# Open questions

Rule 6: record anything unverified here before coding against it. Update the row when answered.

| # | Question (master prompt section 12) | Status, 2026-11-22 | Notes |
|---|---|---|---|
| 1 | Exact API-tool definition format; how tools read and write agent variables | Answered | API tool is set up in the tool editor (Params, Headers, Body). Type `@` in Body/Params/Headers to insert agent or call-context variables, substituted at request time (e.g. `"customer_id": "@customer_id"`). Write back via Advanced > "Save reply into variables" (map response fields to agent variables). https://docs.sarvam.ai/voice-agents/build/tools/https-tool |
| 2 | Names of call-context variables available to tools and hooks | Answered | Tools: User Identifier (caller phone; populated on inbound only, on outbound use the campaign contact number), Call Transcript, Interaction ID, Call Length. Sarvam variables: `current_date`, `current_time`, `current_datetime`, `current_day`, `start_datetime`, `language_name`. https://docs.sarvam.ai/voice-agents/build/tools/https-tool , https://docs.sarvam.ai/voice-agents/build/variables-personalization . On-start hook request payload fields: docs silent as of 2026-11-22 (the post-call inbound webhook uses `user_phone_number`, E.164). |
| 3 | Any live event or transcript stream during a call? | Open | Console assumes `report_signal` plus the post-call transcript. Docs silent as of 2026-11-22: webhooks fire only after the call ends; Analytics API (transcript, trace) is post-call. https://docs.sarvam.ai/voice-agents/api/analytics/overview |
| 4 | Do nudges appear in `interaction_transcript`? | Open | `sarvam.py` has a helper for "ends in unanswered nudges"; verify the shape. Docs silent as of 2026-11-22 (turns are `role` agent/user plus `en_text`; nudges not mentioned). |
| 5 | How nudge delays add up; total time to hang-up | Open | Target about 40 s of silence in total. Docs: each nudge has a message and a delay in seconds of silence before it fires; nudges play in order; "Hang up after unanswered nudges" ends the call after all have played. Whether delays are cumulative is not stated. Docs silent as of 2026-11-22. https://docs.sarvam.ai/voice-agents/build/conversation-settings |
| 6 | Webhook delivery latency; signing-secret format | Open | Signature format is documented: `Sarvam-Signature: sha256=<hex>` (HMAC-SHA256 of `"<timestamp>.<raw_body>"` with the signing secret) plus `Sarvam-Timestamp` (unix seconds); reject if older than 5 min; secret shown once when the webhook config is created; only stored configs (`webhook_id`) are signed, inline URLs are unsigned. https://docs.sarvam.ai/voice-agents/settings/webhooks , https://docs.sarvam.ai/voice-agents/api/campaigns/webhooks/webhook-payload . Latency: docs silent as of 2026-11-22 (only "fires after the call ends"); measure on the first live call. |
| 7 | Network allowlisting for API tools | Answered | Allowlist Sarvam egress IPs `4.213.167.70` and `35.154.84.150`. https://docs.sarvam.ai/voice-agents/build/tools/https-tool |
| 8 | Divyam base URL, auth header, model names | Open | WS5 not started. |
| 9 | Outbound rate limits; ring time before `no_answer` | Open | Scenario tests assume a 25 s ring. Rate limits are documented: plan-wide, shared across campaigns, instant outbound and inbound; Pay as you go 4 concurrent / 20 calls started per min, Pro 10/50, Growth 30/150, Business 200/800; excess calls are queued or rejected. https://docs.sarvam.ai/voice-agents/pricing . Ring time: no configurable timeout documented; the dialing-rate page uses ~30 s only as a sizing estimate (https://docs.sarvam.ai/voice-agents/deploy/campaigns/dialing-rate). Docs silent as of 2026-11-22. |
| 10 | Can the agent end the call itself after a goodbye? | Answered | Yes. The built-in End Call core tool is always available (no setup); the LLM calls it when the conversation is done. State end conditions explicitly in the prompt. https://docs.sarvam.ai/voice-agents/build/tools/core-tools |
| 11 | Can telephony report a missed call to a URL? | Open | `ENTRY_MODE=inbound` for the MVP. Docs silent as of 2026-11-22 (no missed or unanswered inbound event; `no_answer` webhooks exist only for outbound attempts). |
| 12 | Does the inbound webhook carry the same fields as outbound? | Answered | No. Shared: `app_id`, `app_version`, `interaction_id`, `user_phone_number`, `agent_phone_number`, `duration`, `start_datetime`, `end_datetime`, `final_agent_variables`, `output_agent_variables`, `interaction_transcript`, `metadata`. Inbound only: `deployment_id`, `indic_text` per transcript turn. Campaign only: `campaign_id`, `cohort_id`, `attempt_id`, `completion_status`, `connectivity_status`, `next_action_status`, `failure_reason`, `retry_attempt`, `executed_at`, `initial_agent_variables`, `experiment`, `user_identifier`. For inbound, the delivery `attempt_id` is the `interaction_id`. https://docs.sarvam.ai/voice-agents/api/deployments/webhooks/webhook-payload , https://docs.sarvam.ai/voice-agents/api/campaigns/webhooks/webhook-payload |
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

- Webhook signature header name is assumed to be `X-Sarvam-Signature` with HMAC-SHA256 over the raw body; verification is skipped when `SARVAM_WEBHOOK_SECRET` is empty (open question 6). **Docs say otherwise (2026-11-22):** `Sarvam-Signature: sha256=<hex>` over `"<Sarvam-Timestamp>.<raw_body>"`; fix the backend.
- On-start hook caller field is guessed: the code tries `caller_number`, `from`, `user_phone_number`, `phone` (open question 2).
- Call end time is taken as webhook arrival time, so the 30 s valid-end window includes delivery latency (open question 6).
- Alert-page tokens are random and stored with a 24 h expiry in SQLite, not signed as section 6 says. Swap for a signed token before any public deployment of the backend.
- The alert-page link is pushed to the console stream only; SMS and the QR code are not built.
- `truck_status` uses wall-clock time, so outside night hours `time_now` and `minutes_since_last_rest` look odd; the web console runs its own simulated clock for the stage demo.

