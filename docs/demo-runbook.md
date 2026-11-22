# Demo runbook (3 minutes, Virtual mode)

Virtual mode runs the decision logic with simulated call outcomes and places no calls. It is the stage plan for 2026-11-22; Live mode needs the Sarvam agents and a public URL (see `docs/sarvam-setup.md`).

## Before going on stage

1. `bash scripts/dev.sh` (or the Conductor Run button). Open `http://localhost:8001/demo` full-screen in a dark-theme browser; zoom so the console fills the projector.
2. Open the alert page on a phone or a second tab: `http://localhost:8001/a/demo?reason=not_answering`.
3. Set speed to **4x** for the escalation scene, **1x** for the conversation.
4. Record a backup video of the whole run (QuickTime, screen + mic) and keep it on the desktop.

## Script

**0:00 The problem (15 s).** "A khalasi was the helper who sat beside the driver through the night. Trucks lost him to cost cutting. Khalasi brings him back as a phone call, in the driver's own language."

**0:15 Scene 1, the call (60 s).** Press **Start call**. Raju's missed call at 12:10 am; Khalasi calls back. Point at the transcript: Hindi first, English below. Watch the flags appear: slow reply, yawn, confused answer. The meter moves green → amber. Khalasi names Sharma Dhaba from `truck_status`, Raju promises to stop. Say: "No LLM decides to alert anyone. Every call-back and alert comes from a tested decision engine with 29 scenario tests."

**1:15 Scene 2, silence at a dhaba (20 s).** Switch the truck to **Stopped at dhaba**, press **No answer**. The log says "no escalation". Say: "Silence while parked at a known stop is rest, not an emergency."

**1:35 Scene 3, silence while moving (60 s).** Switch to **Moving**, press **No answer**, set **4x**. The kilometre stones light up: nudge at 0:15, call-back at 0:45, second try at 1:30, **Sunita alerted at 2:30**. Flip to the phone: the alert page in Hindi, last location, Call Raju, Call 112, "He's safe". Press **Sunita: He's safe**, then the console shows Khalasi calling Raju back.

**2:35 Scene 4, the dark stretch (25 s).** Reset, Start call, press **Dark stretch ahead** at 1x. Khalasi states when he left, the time now, how long the stretch lasts and how far Jhansi is, and offers Apna Ghar. Raju refuses; the log schedules a call for the stretch exit. Say: "Fail safe: stale GPS counts as moving, and a call that ends without a logged state is treated as an emergency."

**3:00 Close.** "Fleets see alerts and rest events, never transcripts. Everything synthetic on screen says Simulated. Next: live Sarvam calls on one fixed number, and a 100-truck pilot design."

## If something breaks

- Console frozen: press **Reset**, then Start call again.
- Browser dies: play the backup video.
- Question about live calls: show `backend/app/engine.py` and `pytest -q` output instead of placing a call.

## Presentation outline for 4 pm

1. Problem and the name (1 slide).
2. The product is a phone call, not an app (1 slide, the phone number and the three agents: driver call, alert call, console).
3. How it works: architecture diagram from `docs/architecture.md`; safety logic is plain code (1 slide).
4. Live demo, this runbook (3 min).
5. Honest status: what is real (engine, tests, console, alert page, agent instructions) and what is simulated or pending (Sarvam agents, telephony, Divyam, pilot data) (1 slide).
6. Pilot plan and ask (1 slide): 100 trucks, 12 weeks, metrics from master prompt section 9.
