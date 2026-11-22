# Sarvam agent setup (WS2)

Status, 2026-11-22: **not yet created in Sarvam.** Create both agents through the `sarvam-voice-agents` MCP in a session signed in with Sarvam SSO, then fill in every row below with the setting name the dashboard actually uses and any manual UI steps. Instructions live in `agents/khalasi.md` and `agents/khalasi_alert.md`; paste them verbatim.

## Khalasi (driver agent)

| Setting | Value | Done |
|---|---|---|
| Instruction | `agents/khalasi.md`, verbatim | |
| Starting language | Hindi | |
| Languages allowed | Hindi, English, Punjabi, Marathi, Tamil, Telugu, Kannada, Bengali | |
| Switch language during call | On | |
| Temperature (if offered) | 0.3 | |
| Let callers interrupt | On | |
| Background sound | None | |
| Sound sensitivity | Medium; tune with a noisy cabin recording | |
| Nudge quiet callers | On. Nudge 1 at ~15 s: "Ustaad? Ustaad, bas 'haan' bolo!" Nudge 2 at ~30 s: "Ustaad! Haan bolo!" Generate translations. Check how delays add up (open question 5). | |
| Hang up after unanswered nudges | On, about 40 s of silence in total | |
| Max call length | 60 minutes | |
| Important words | Ustaad, dhaba, Apna Ghar, NH-44, Nagpur, Seoni, Lakhnadon, Sagar, Lalitpur, Jhansi | |
| Protect sensitive info | On | |
| Voicemail | Off | |
| Welcome message (inbound) | "Ustaad! Khalasi bol raha hoon." | |

- Input variables: `driver_name`, `alert_contact_name`, `destination`, `first_call_tonight`, `call_reason`, `trip_id`.
- Output variable: `call_end_state` = `parked_resting` / `driving_alert` / `unknown`. Console labels and metrics only; it never changes a decision.
- API tools (header `Authorization: Bearer $TOOL_SECRET`, `trip_id` in every body): `truck_status`, `log_status`, `report_signal`. Contracts in master prompt section 6; endpoints in `backend/app/main.py`.
- On-start hook for inbound calls: `POST $PUBLIC_BASE_URL/hooks/on-start`.
- Outbound first line: the backend sets `initial_bot_message` per `call_reason` (openers in `agents/khalasi.md`).

## Khalasi Alert (family agent)

Outbound only, max call length 2 minutes, nudges off. Instruction `agents/khalasi_alert.md`. Input variables: `contact_name`, `driver_name`, `alert_reason`, `last_location`, `last_seen_time`, `is_fleet_desk`.

## Telephony

One fixed number for every call, in and out, saved by drivers as "Khalasi". Business Name Display "Khalasi" if offered. Put `SARVAM_CONNECTION_ID` and `SARVAM_AGENT_PHONE` in `.env`. Deploy inbound on the same number with the webhook at `$PUBLIC_BASE_URL/webhooks/sarvam`. Public HTTPS: a cloudflared tunnel in development (`cloudflared` is not installed on this Mac yet).

## Rehearsal

Use Sarvam's Mock API tool and the test agent before pointing tools at the real backend. Only numbers in `ALLOWED_NUMBERS` may be called; keep `CALLS_ENABLED=false` until the demo rehearsal.
