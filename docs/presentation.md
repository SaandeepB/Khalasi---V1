# Khalasi, 5-minute pitch + 3-minute demo

Six slides. Speaker notes in *italics*. Fill the two bracketed numbers after the final test run.

## 1. The khalasi is gone

- A khalasi was the helper who sat beside a truck driver through the night: company, a second pair of eyes, a nudge to stop.
- Cost cutting removed him. Night runs on NH-44 are now one tired man, alone, for 10 hours.
- Drowsy driving is the quiet killer on Indian highways; the driver is also the one who pays.

*We are not building an app for drivers. Drivers don't look at phones at 1 am. We bring the khalasi back.*

## 2. The product is a phone call

- Khalasi is a Sarvam voice agent. The driver saves one number as "Khalasi" and gives it a missed call when he leaves.
- It talks in his language (Hindi, Punjabi, Marathi, Tamil, Telugu, Kannada, Bengali), one sentence at a time while the truck moves.
- It hears sleepiness in the conversation and gets him to a named safe stop. If he goes silent while moving: nudge, call back, then his family.
- Before a known no-network stretch, if he hasn't rested in 5 hours, it asks him to stop first.

*Three voices: Khalasi for the driver, Khalasi Alert for the family, and a console for the demo team. Nothing to install.*

## 3. Safety logic is plain code

- Every call-back, wait and alert is decided by a pure function: `decide(state, event, now) -> (new_state, actions)`.
- No LLM decides to alert anyone, and no LLM output can cancel an alert.
- Fail safe: stale GPS counts as moving; a call that ends without a logged state is treated as an emergency.
- [N] scenario tests from the spec pass, covering silence at a dhaba vs on the highway, no-network stretches, promised stops, quiet mode, driver swaps, kill switch and allowlist.

*Show the architecture diagram from docs/architecture.md. Point at the engine file if asked.*

## 4. Demo (3 minutes)

Follow `docs/demo-runbook.md`: the call with sleep signs, silence at a dhaba, silence while moving to Sunita's phone at 2:30, the dark-stretch warning.

*Virtual mode: the real decision logic with simulated call outcomes. Everything synthetic on screen says Simulated.*

## 5. Honest status

Real today: agent instructions (Appendix A and B), decision engine with tests, demo console from the Figr design, family alert page, outbound-call guard rails (kill switch, allowlist, 12 calls per driver per hour, alerts never capped).

Pending: the two Sarvam agents on a fixed number, public HTTPS for tools and webhooks, post-call analysis through Divyam, night-ops and pilot screens, pilot data generator. [M] open questions logged in docs/open-questions.md.

*Say this plainly. Judges trust teams that know what is simulated.*

## 6. Pilot and the ask

- 100 trucks, assigned at random by truck, 12 weeks, one fleet partner on NH-44.
- Measure: warnings that ended in a rest stop, night driving hours (guardrail: must not rise), harsh braking and crashes per lakh km, promised stops kept, false alarms per family per month, stops before a dark stretch, drivers still calling each week.
- Driver-first privacy: fleets see alerts and rest events, never transcripts. Location only during an active alert. Transcripts deleted after 30 days.
- Ask: a fleet partner, a telephony number, and Sarvam credits for the pilot.

*Close on the name: the helper who sits beside him, back on the night run.*
