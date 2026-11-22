# Design map

Figr is the design source of truth (rule 10). Figr project: `khalasi`. Verbatim export: `design/figr-export/khalasi/`. Where a design conflicts with the rules, the rules win and the difference is logged here.

| Figr design | Route | Component | Status | Differences |
|---|---|---|---|---|
| Demo console · ready (`scr_demo`) | `/demo` | `web/src/screens/DemoConsole.tsx` | Ported from export | "Simulated · Virtual mode" badge added in the top bar (rule 8). |
| Demo console · sleep warning (`scr_demo_sleep`) | `/demo?figr_screen=scr_demo_sleep` | same | Ported | Same badge. |
| Demo console · dark stretch (`scr_demo_dark`) | `/demo?figr_screen=scr_demo_dark` | same | Ported | Same badge. |
| Demo console · Sunita alerted (`scr_demo_alert`) | `/demo?figr_screen=scr_demo_alert` | same | Ported | Same badge. |
| Demo console · phone unreachable (`scr_demo_unreachable`) | `/demo?figr_screen=scr_demo_unreachable` | same | Ported | Same badge. |
| Alert page | `/a/:token` | `web/src/screens/AlertPage.tsx` | **Not in Figr**, built plainly from tokens | Hindi first, English below; reasons not_answering and unreachable; Call Raju, Call 112, He's safe → false alarm question. |
| Night operations | `/ops` | `web/src/screens/NightOps.tsx` | **Not in Figr**, built plainly from tokens | Drivers with every state incl. unregistered (R13), alerts feed with chain steps; location only during an active alert; no map, transcripts or summaries. Simulated data. |
| Pilot results | `/pilot` | `web/src/screens/PilotResults.tsx` | **Not in Figr**, built plainly from tokens | Seeded generator in `web/src/pilot/`; every chart labelled Simulated. |
| Driver setup | `/setup` | `web/src/screens/DriverSetup.tsx` | **Not in Figr**, built plainly from tokens | Language, contact, consent (section 9 copy, "dhai minute"), required test-call step; nothing saved. Romanised Hindi needs a native-speaker pass. |
| Parked home | `/home` | `web/src/screens/ParkedHome.tsx` | **Not in Figr**; `screens/Home.tsx` in the export is Figr's blank placeholder | Trip clock, driver today, next safe stop, call Khalasi, no-phone-in-hand note. Simulated values. |

## Tokens

`design/figr-export/khalasi/index.css` → `web/src/design/tokens.css`, unchanged `@theme` block: night surfaces (`night`, `panel`, `raised`, `line`, `line-strong`), text (`ink`, `ink-muted`, `ink-faint`), accents (`magenta`, `teal`, `marigold`), escalation (`safe`, `warn`, `danger` plus `-deep`), radii `panel` 14px and `control` 10px, fonts Mukta and IBM Plex Mono.

## States checked against Figr (section 9)

Present in the Demo console: before the dark stretch, promised stop, quiet mode, unreachable vs no answer, each alert-chain step as event-log lines. Missing: care mode, driver swap, alert-chain steps as their own screens. Ask the user before designing these.

## Screenshots (built screens, for comparison with Figr)

Captured with `bash scripts/screenshots.sh` against the production build; Figr side by side goes in the PR.

| Figr design | Built screenshot |
|---|---|
| Demo console · ready | `docs/screenshots/demo-ready.png` |
| Demo console · sleep warning | `docs/screenshots/demo-sleep-warning.png` |
| Demo console · dark stretch | `docs/screenshots/demo-dark-stretch.png` |
| Demo console · Sunita alerted | `docs/screenshots/demo-sunita-alerted.png` |
| Demo console · phone unreachable | `docs/screenshots/demo-unreachable.png` |
| Alert page, not answering (Not in Figr) | `docs/screenshots/alert-not-answering.png` |
| Alert page, unreachable (Not in Figr) | `docs/screenshots/alert-unreachable.png` |
| Night operations (Not in Figr) | `docs/screenshots/night-ops.png` |
| Pilot results (Not in Figr) | `docs/screenshots/pilot-results.png` |
| Driver setup (Not in Figr) | `docs/screenshots/driver-setup.png` |
| Parked home (Not in Figr) | `docs/screenshots/parked-home.png` |
