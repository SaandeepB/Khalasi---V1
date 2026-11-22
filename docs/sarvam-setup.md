# Sarvam agent setup (WS2)

Status, 2026-11-22: **both agents created in Sarvam through the `sarvam-voice-agents` MCP** (see "Created in Sarvam on 2026-11-22" below). Instructions live in `agents/khalasi.md` and `agents/khalasi_alert.md` and were pasted verbatim. Done column: yes = applied through the MCP; manual = do it in the dashboard; not available = the platform does not offer it as specified.

## Khalasi (driver agent)

| Setting | Value | Done |
|---|---|---|
| Instruction | `agents/khalasi.md`, verbatim | yes (single-prompt mode, state `start`) |
| Starting language | Hindi | yes (`language_config.initial_language_name`) |
| Languages allowed | Hindi, English, Punjabi, Marathi, Tamil, Telugu, Kannada, Bengali | yes (`language_config.supported_languages`) |
| Switch language during call | On | yes (`enable_language_identification`, `enable_lid`, `change_output_language` tool) |
| Temperature (if offered) | 0.3 | yes (`llm_config.temperature`) |
| Let callers interrupt | On | yes (`interaction_config.allow_interrupt_during_playback`) |
| Background sound | None | yes (`output_config.background_sound.enabled = false`; template default was quiet_office) |
| Sound sensitivity | Medium; tune with a noisy cabin recording | manual (VAD `speech_frame_config` left at platform default; MCP offers volume_threshold -50..-20 and silence_duration_frames 4/6/9/12, no "Medium" label) |
| Nudge quiet callers | On. Nudge 1 at ~15 s: "Ustaad? Ustaad, bas 'haan' bolo!" Nudge 2 at ~30 s: "Ustaad! Haan bolo!" Generate translations. Check how delays add up (open question 5). | yes (two nudges, `timeout_seconds` 15 and 15, translations auto-generated). Assumes each timeout counts from the previous nudge; if they are absolute, change nudge 2 to 30. Verify (open question 5). |
| Hang up after unanswered nudges | On, about 40 s of silence in total | yes (`end_interaction_after_consecutive_nudges = true`); exact total time unverified |
| Max call length | 60 minutes | not available (MCP caps `max_interaction_time_seconds` at 1500 = 25 min; set to 1500). Backend must call back for longer runs, or raise in dashboard if allowed. |
| Important words | Ustaad, dhaba, Apna Ghar, NH-44, Nagpur, Seoni, Lakhnadon, Sagar, Lalitpur, Jhansi | yes (`speech_to_text_config.speech_hotwords`) |
| Protect sensitive info | On | yes, platform default `privacy_config` (phone numbers and emails masked and hashed). Confirm the dashboard toggle reads On. |
| Voicemail | Off | yes (`configure_voicemail enabled=false`) |
| Welcome message (inbound) | "Ustaad! Khalasi bol raha hoon." | yes (`intro_message_config.audio`; translations auto-generated) |

- Input variables: `driver_name`, `alert_contact_name`, `destination`, `first_call_tonight`, `call_reason`, `trip_id`. Done (agent variables, call-start inputs). Template variables `user_name` and `call_summary` removed.
- Output variable: `call_end_state` = `parked_resting` / `driving_alert` / `unknown`. Done (enum, `update_post_interaction = true`). Console labels and metrics only; it never changes a decision.
- API tools: `truck_status`, `log_status`, `report_signal`. Done as `webhook` tools, POST, `trip_id` bound from the agent variable in every body, `state` / `type` / `detail` filled by the agent (enums as in master prompt section 6), timeout 3 s, **mock responses on** (section 6 sample bodies). URL is the placeholder `https://PUBLIC-BASE-URL.example/tools/{truck-status,log-status,report-signal}`.
- On-start hook for inbound calls: `POST $PUBLIC_BASE_URL/hooks/on-start`. Manual (not configured).
- Outbound first line: the backend sets `initial_bot_message` per `call_reason` (openers in `agents/khalasi.md`).

## Khalasi Alert (family agent)

| Setting | Value | Done |
|---|---|---|
| Instruction | `agents/khalasi_alert.md`, verbatim | yes |
| Outbound only | | not available as an agent setting; outbound vs inbound is decided by campaign vs deployment. Just never deploy it inbound. |
| Max call length | 2 minutes | yes (`max_interaction_time_seconds = 120`) |
| Nudges | Off | yes |
| Input variables | `contact_name`, `driver_name`, `alert_reason`, `last_location`, `last_seen_time`, `is_fleet_desk` | yes |
| Languages | Hindi start, same eight as Khalasi | yes |
| Background sound | None | yes |

## Created in Sarvam on 2026-11-22

| Agent | App id | Committed version | Open draft |
|---|---|---|---|
| Khalasi | `Khalasi-2b130551-4f0f` | 1 | 2 |
| Khalasi Alert | `Khalasi-Ale-97e39936-cce8` | 1 | 2 |

Khalasi tool ids: `truck_status` 3be01013-3db8-403a-961a-25e47c2c43c1, `log_status` 060eb91f-8164-4d7e-86e1-97ce03aa822a, `report_signal` a8bbc991-7ed3-47af-81ed-65d05cc6dd1a. Voice: template default (internal_id 01a0cf16-7179-7472-b7df-b7b432d5faa5, pace 1.15) on both agents.

Applied through the MCP: instructions, languages and switching, temperature, interruptions, background sound off, nudges and hang-up, max length (capped), hotwords, voicemail off, welcome message, input and output variables, three API tools with mock bodies, commit of version 1.

Manual steps still needed:
1. **Tool auth.** The MCP refuses auth on tools. In the console, store `TOOL_SECRET` as a workspace credential and select it as Bearer auth on each of the three tools (giving `Authorization: Bearer <TOOL_SECRET>`).
2. **Tool URLs.** `create_api_tool` refuses unresolvable hosts, so the tools were saved with the registry writer and the placeholder host. Replace with the real `$PUBLIC_BASE_URL/tools/...` once the tunnel exists, then turn **mock off** on each tool.
3. **Sound sensitivity.** Pick Medium in the dashboard (or a volume threshold) and tune with a cabin recording.
4. **Max call length.** 60 min not offered (cap 25 min). Check the dashboard; otherwise rely on the backend `check_in` callbacks.
5. **Nudge timing.** Confirm whether nudge timeouts are cumulative; adjust nudge 2 to 15 or 30 s so silence to hang-up is ~40 s.
6. **Protect sensitive info.** Confirm the toggle is On (privacy_config with phone masking is present).
7. **Voice.** Choose a male Hindi voice if the template default does not fit (`agents(list_voices)`).
8. **On-start hook** for inbound, telephony, deployment and webhook: not done (out of scope for this session; no numbers, deployments or calls were made).
9. Commit a new version after any manual change and point deployments/campaigns at it.

## Telephony

One fixed number for every call, in and out, saved by drivers as "Khalasi". Business Name Display "Khalasi" if offered. Put `SARVAM_CONNECTION_ID` and `SARVAM_AGENT_PHONE` in `.env`. Deploy inbound on the same number with the webhook at `$PUBLIC_BASE_URL/webhooks/sarvam`. Public HTTPS: a cloudflared tunnel in development (`cloudflared` is not installed on this Mac yet).

## Rehearsal

The three tools currently answer with mock bodies, so the test agent can be rehearsed before the backend is public. Only numbers in `ALLOWED_NUMBERS` may be called; keep `CALLS_ENABLED=false` until the demo rehearsal.

## Test calls without our own number (found 2026-11-22)

Sarvam can dial a **verified** phone over its own line, so a real call to a teammate needs no telephony connection:

1. `verify_phone_number` (MCP) with the number in E.164 sends an SMS code (`status: otp_dispatched`, valid about 15 minutes, resend after 60 s). Call it again with `otp` to finish (`status: validated`); `telephony list_verified_numbers` confirms.
2. `place_test_call` with `app_id`, `app_version` (committed version), `phone_numbers` (verified, E.164, up to 10) and `app_variables` (the six Khalasi input variables were accepted). `success: true` means queued to dial, not connected. Costs credits per minute.
3. Outcome and transcript appear a few minutes later in the `attempts` and `interactions` analytics reports, then `analytics transcript`.

First real call: 2026-11-22 16:37 IST, Khalasi version 1, `call_reason=check_in`, to a teammate's verified number (the only entry in `ALLOWED_NUMBERS`), attempt `5b77c269-8637-4bfa-8d45-f34a2c6b4e27`. Tools were still on mock data and the placeholder URL, so `truck_status` returned the section 6 sample and nothing reached our backend. Test numbers are not for family contacts: rule 7 still applies.
