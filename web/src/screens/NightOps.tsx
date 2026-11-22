// Not in Figr: built plainly from design tokens
// Night operations desk (/ops). Desktop, for the fleet night desk.
// Rule 4: fleets see alerts and rest events only. No live map, no transcripts, no summaries;
// last known location appears only on rows with an active alert. Rule 8: all data is simulated.
import { useEffect, useState, type ReactNode } from "react";
import {
  Coffee,
  MapPin,
  Moon,
  PhoneCall,
  PhoneMissed,
  PhoneOff,
  Timer,
  UserRoundX,
  type LucideIcon,
} from "lucide-react";
import {
  ALERTS,
  CHAIN_STEPS,
  DRIVERS,
  REASON_LABEL,
  STATE_META,
  STEP_LABEL,
  type Alert,
  type Driver,
  type DriverState,
  type Tone,
} from "./nightops.data";

const STATE_ICON: Record<DriverState, LucideIcon> = {
  talking: PhoneCall,
  resting: Coffee,
  before_dark: Moon,
  in_dark: Moon,
  promised_stop: Timer,
  no_response: PhoneMissed,
  family_unreachable: PhoneOff,
  unregistered: UserRoundX,
};

const toneChip: Record<Tone, string> = {
  safe: "border-safe/50 bg-safe-deep text-safe",
  warn: "border-warn/50 bg-warn-deep text-warn",
  danger: "border-danger/50 bg-danger-deep text-danger",
  neutral: "border-line-strong bg-raised text-ink-muted",
};

const IST_TIME = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
  hour12: true,
});
const IST_DATE = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  weekday: "short",
  day: "numeric",
  month: "short",
});

function useIstClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function NightOps() {
  const now = useIstClock();
  const activeAlerts = DRIVERS.filter((d) => d.activeAlert).length;
  const resting = DRIVERS.filter((d) => d.state === "resting").length;
  const openAlerts = ALERTS.filter((a) => a.open).length;

  return (
    <div className="flex min-h-screen flex-col bg-night text-ink">
      <header className="flex h-[76px] shrink-0 items-center justify-between gap-8 border-b border-line bg-panel px-6">
        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-bold tracking-tight text-magenta">Khalasi</span>
          <span className="text-lg text-ink-muted">· Night operations</span>
          <SimChip large />
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right leading-tight">
            <div className="font-mono text-2xl font-medium tabular-nums">{IST_TIME.format(now)}</div>
            <div className="text-base text-ink-muted">
              Shift clock · IST · {IST_DATE.format(now)} · Night shift 8:00 pm to 6:00 am
            </div>
          </div>
          <div className="h-8 w-px bg-line" />
          <div className="grid size-10 place-items-center rounded-full bg-raised text-base font-semibold text-teal">
            ND
          </div>
        </div>
      </header>

      <main className="grid flex-1 grid-cols-[minmax(0,1fr)_440px] gap-4 p-5">
        <DriverBoard drivers={DRIVERS} activeAlerts={activeAlerts} resting={resting} />
        <AlertsFeed alerts={ALERTS} open={openAlerts} />
      </main>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-6 py-3 text-sm text-ink-faint">
        <span>
          Fleets see alerts and rest events only. No transcripts, no summaries, no live map. Location appears only
          during an active alert.
        </span>
        <span className="font-mono">Simulated data · Times in IST</span>
      </footer>
    </div>
  );
}

/* ---------- Driver board ---------- */

function DriverBoard({
  drivers,
  activeAlerts,
  resting,
}: {
  drivers: Driver[];
  activeAlerts: number;
  resting: number;
}) {
  return (
    <section aria-label="Opted-in drivers" className="flex min-w-0 flex-col rounded-panel border border-line bg-panel">
      <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
        <div className="flex items-baseline gap-3">
          <h2 className="text-lg font-semibold">Opted-in drivers</h2>
          <span className="text-base text-ink-muted">{drivers.length} on the road tonight</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Chip tone="danger">
            {activeAlerts} active alert{activeAlerts === 1 ? "" : "s"}
          </Chip>
          <Chip tone="safe">{resting} resting</Chip>
          <SimChip />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-base">
          <thead>
            <tr className="text-sm tracking-wide text-ink-faint uppercase">
              <th scope="col" className="px-5 py-3 font-medium">
                Driver
              </th>
              <th scope="col" className="px-3 py-3 font-medium">
                Truck
              </th>
              <th scope="col" className="px-3 py-3 font-medium">
                Route
              </th>
              <th scope="col" className="px-3 py-3 font-medium">
                State
              </th>
              <th scope="col" className="px-3 py-3 font-medium">
                Note
              </th>
              <th scope="col" className="px-5 py-3 font-medium">
                Last known · active alert only
              </th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d) => (
              <DriverRow key={d.id} d={d} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DriverRow({ d }: { d: Driver }) {
  const meta = STATE_META[d.state];
  const Icon = STATE_ICON[d.state];
  const alert = Boolean(d.activeAlert);
  return (
    <tr className={`border-t border-line/60 ${alert ? "bg-danger-deep/40" : ""}`}>
      <td className="px-5 py-3 align-top">
        <div className="font-semibold">{d.name}</div>
        {d.sub && <div className="text-sm text-ink-faint">{d.sub}</div>}
      </td>
      <td className="px-3 py-3 align-top font-mono text-sm whitespace-nowrap text-ink-muted">{d.truck}</td>
      <td className="px-3 py-3 align-top text-ink-muted">{d.route}</td>
      <td className="px-3 py-3 align-top">
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-sm font-medium whitespace-nowrap ${toneChip[meta.tone]}`}
        >
          <Icon size={14} strokeWidth={2} />
          {meta.label}
        </span>
      </td>
      <td className="px-3 py-3 align-top text-sm text-ink-muted">{d.note}</td>
      <td className="px-5 py-3 align-top text-sm">
        {alert && d.lastKnown ? (
          <span className="inline-flex items-center gap-1.5 text-ink">
            <MapPin size={14} strokeWidth={2} className="shrink-0 text-danger" />
            {d.lastKnown.place} · {d.lastKnown.time} IST
          </span>
        ) : (
          <span className="text-ink-faint">—</span>
        )}
      </td>
    </tr>
  );
}

/* ---------- Alerts feed ---------- */

function AlertsFeed({ alerts, open }: { alerts: Alert[]; open: number }) {
  return (
    <section aria-label="Alerts feed" className="flex flex-col rounded-panel border border-line bg-panel">
      <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
        <h2 className="text-lg font-semibold">Alerts feed</h2>
        <div className="flex items-center gap-2 text-sm">
          <Chip tone={open > 0 ? "danger" : "neutral"}>{open} open</Chip>
          <SimChip />
        </div>
      </div>
      <ol className="flex flex-col divide-y divide-line/60">
        {alerts.map((a) => (
          <AlertItem key={a.id} a={a} />
        ))}
      </ol>
    </section>
  );
}

function AlertItem({ a }: { a: Alert }) {
  const stepIndex = CHAIN_STEPS.indexOf(a.step);
  return (
    <li className={`flex flex-col gap-2 px-5 py-4 ${a.open ? "bg-danger-deep/30" : ""}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-sm text-ink-muted tabular-nums">{a.time} IST</span>
        <Chip tone={a.open ? "danger" : "neutral"}>{a.open ? "Open" : "Resolved"}</Chip>
      </div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-semibold">{a.driver}</span>
        <span className="font-mono text-sm text-ink-faint">{a.truck}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-ink-faint">Reason</span>
        <Chip tone={a.open ? "danger" : "warn"}>{REASON_LABEL[a.reason]}</Chip>
      </div>
      <ol aria-label="Alert chain" className="flex flex-wrap items-center gap-1 text-xs">
        {CHAIN_STEPS.map((s, i) => {
          const current = s === a.step;
          const reached = i <= stepIndex;
          return (
            <li key={s} className="flex items-center gap-1">
              {i > 0 && <span className="text-ink-faint">→</span>}
              <span
                className={`rounded px-1.5 py-0.5 ${
                  current
                    ? "border border-line-strong bg-raised font-medium text-ink"
                    : reached
                      ? "text-ink-muted"
                      : "text-ink-faint"
                }`}
              >
                {STEP_LABEL[s]}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="text-sm text-ink-muted">{a.resolution}</p>
    </li>
  );
}

/* ---------- Small bits ---------- */

function Chip({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={`rounded-md border px-2 py-0.5 text-sm font-medium whitespace-nowrap ${toneChip[tone]}`}>
      {children}
    </span>
  );
}

function SimChip({ large = false }: { large?: boolean }) {
  return (
    <span
      className={`self-center rounded-md border border-warn/50 bg-warn-deep font-medium text-warn ${
        large ? "px-2.5 py-1 text-base" : "px-2 py-0.5 text-sm"
      }`}
    >
      Simulated
    </span>
  );
}
