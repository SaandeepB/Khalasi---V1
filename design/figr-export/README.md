# Figr exports (reference only)

Verbatim code exports from the Khalasi Figr project, downloaded by hand on 2026-11-22.
Do not edit these files. Port tokens and components from here into `web/src/design/` and
`web/src/` (WS0, WS3, WS4), and record each mapping in `docs/design-map.md`.

| Export | Contents | Figr screens |
|---|---|---|
| `khalasi/` | Tailwind v4 tokens (`index.css`), demo simulation (`demo/engine.ts`), Demo console screen (`screens/DemoConsole.tsx`), router and manifest | Demo console: ready, sleep warning, dark stretch, Sunita alerted, phone unreachable (`screens.figr.json`) |

Not in this export: alert page, night operations, pilot results, driver setup, parked home
(`screens/Home.tsx` is Figr's placeholder). Where a design is missing, ask the user; see section 9 of
`docs/MASTER_PROMPT.md`.
