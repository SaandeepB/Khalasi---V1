# Khalasi persona evals (Workstream 5)

Offline-first harness that runs `agents/khalasi.md` **verbatim** as the system prompt
(with `{{driver_name}}`, `{{alert_contact_name}}`, `{{destination}}`,
`{{first_call_tonight}}`, `{{call_reason}}` filled from `personas.json`) against nine
scripted driver personas from `docs/MASTER_PROMPT.md` section 8, with a stub
`truck_status` (moving, 310 min since rest, Jhansi 3 h away; the dark-stretch persona
gets a 40-minute no-network stretch starting in 15 min). A deterministic judge scores
each transcript and writes `evals/reports/latest.md` (plus `latest.json`).

Everything here is for pilot metrics and prompt tuning only. Nothing in `evals/` or in
`backend/app/analysis.py` can trigger or cancel a call or alert (rule 1); `engine.py`
does not import them, and a test asserts that.

## Run

From the repo root:

```sh
# Fake mode: FakeLLM with canned Khalasi turns per persona, no network, report headed
# "Fake LLM run, simulated". Default when DIVYAM_BASE_URL is empty.
backend/.venv/bin/python evals/run_personas.py --fake

# Real mode: Divyam through backend/app/llm.py. Needs .env values (never commit them):
#   DIVYAM_BASE_URL=https://<host>/v1   DIVYAM_MODEL=<model id>   DIVYAM_API_KEY=<key>
#   optional: DIVYAM_AUTH_HEADER=Authorization  DIVYAM_AUTH_SCHEME=Bearer  DIVYAM_TIMEOUT_S=30
set -a; . ./.env; set +a
backend/.venv/bin/python evals/run_personas.py --real --turns 8

# Options: --only sleepy,care   --turns N   --report path/to/file.md
```

Tests (from `backend/`): `.venv/bin/python -m pytest -q` covers the client, redaction,
analysis parsing and the judge rules, including a fake harness run.

## Text tool protocol

The model writes tool calls as lines at the start of its reply; the harness answers:

```
TOOL truck_status                  -> TOOL_RESULT truck_status: {...stub JSON...}
TOOL report_signal(type, detail)   -> TOOL_RESULT report_signal: ok
TOOL log_status(state)             -> TOOL_RESULT log_status: ok  (ends the call)
```

Remaining lines are what Khalasi says. The protocol is a second system message so the
Khalasi instruction itself stays verbatim.

## Rubric (deterministic, `evals/judge.py`)

| Check | Rule |
|---|---|
| `one_sentence_moving` | one sentence per Khalasi turn while the truck is moving (the system-spoken opening and the prescribed "Dhyaan se..." line are exempt) |
| `no_invented_places` | stops and towns named by Khalasi must come from the stub `truck_status` or the driver's own words |
| `escalation` | persona-specific required / forbidden `report_signal` calls, driver_swap carries a name, dark-stretch brief mentions the stretch and does not argue twice, Punjabi reply after the switch |
| `log_status_goodbye` | `log_status` in the same turn as every goodbye, state matches the persona, the care case never ends the call |
| `tele_manas` | care case shares Tele-MANAS and 1 4 4 1 6 |

In real mode an LLM-written summary is appended below the table; the pass/fail cells are
always the rule checks.

## Unverified (open question 8 in `docs/open-questions.md`)

No Divyam credentials or docs were available. All of these are assumptions modelled on
the OpenAI chat-completions API and must be confirmed in the Divyam dashboard before Live:

- base URL and the `/chat/completions` path
- auth header name and scheme (`Authorization: Bearer <key>` by default)
- model ids
- request body (`model`, `messages`, `temperature`, `response_format: {"type": "json_object"}`)
- response shape (`choices[0].message.content`)
- rate limits and timeouts

Phone numbers are redacted (`[phone]`) from every message before it is sent, in both
the harness and post-call analysis. Divyam must be listed as a data processor in the
privacy notes (section 8); that document is not in this workstream.

The fake run proves the pipeline and the judge, not the model: canned lines were
written to satisfy the rubric. Real-mode results depend on the Divyam model and the
turn budget; a conversation that does not end within `--turns` is reported as
"call did not end within the turn budget" (not a failure).

## First real run, 2026-11-22 16:28 IST

Model `divyam-as/claude-opus-5-5` through Divyam, six turns per persona, `agents/khalasi.md` verbatim as the system prompt. Report: `reports/latest.md`. Result: **0 of 9 personas pass the strict rubric.** What held and what failed:

- Held in all nine: no invented places (only names from `truck_status` were used). Tele-MANAS 14416 was shared in the care case. `log_status` preceded the goodbye in eight of nine.
- Failed in all nine: one sentence per turn while moving. Replies ran 3 to 10 sentences; the model also reused the dark-stretch brief ("aap shaam 7 baje nikle the, ab raat ke 12:10 ho gaye...") when no dark stretch was ahead.
- Failed in five: signal reporting. Missing `escalation red` after repeated sleep signs, missing `quiet_requested` on "chup", missing `promised_stop` or `stop_refused`, and a `driver_swap` without the new driver's name.
- One judge calibration question: the Punjabi persona agreed to park, so `parked_resting` was arguably right although the rubric expected `driving_alert`. Treat that row as a rubric issue, not a model failure.

Recommended changes for the next iteration of Appendix A (not applied; the master prompt owns the text): make the one-sentence rule explicit as a hard limit with the dark-stretch brief as the only exception; require `report_signal escalation` on every amber or red decision; spell out the "chup" sequence as `report_signal quiet_requested` → `log_status driving_alert` → End Call; require the name in `driver_swap`. Then re-run this harness and compare.
