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
| Night operations | `/ops` | not built | Not in Figr | Ask the user for a design before building. |
| Pilot results | `/pilot` | not built | Not in Figr | Ask the user; data must be labelled Simulated. |
| Driver setup | `/setup` | not built | Not in Figr | Ask the user. |
| Parked home | `/home` | not built | Not in Figr; `screens/Home.tsx` in the export is Figr's blank placeholder | Ask the user. |

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
