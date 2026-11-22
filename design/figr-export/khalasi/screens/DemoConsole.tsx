import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  BellRing,
  CirclePause,
  Coffee,
  Info,
  MessageCircleWarning,
  Pause,
  Phone,
  PhoneCall,
  PhoneIncoming,
  PhoneMissed,
  PhoneOff,
  Play,
  RotateCcw,
  ShieldCheck,
  Truck,
  UtensilsCrossed,
  VolumeX,
  WifiOff,
  CalendarClock,
  type LucideIcon,
} from "lucide-react";
import { useScreenInit } from "../useScreenInit";
import {
  ALERT_AT,
  MILESTONES,
  clock,
  darkStretchAhead,
  driverSaysChup,
  hm,
  levelOf,
  mmss,
  noAnswer,
  phoneUnreachable,
  presetSim,
  rajuAnswers,
  setTruck,
  startCall,
  stateLabel,
  sunitaMarksSafe,
  tick,
  initialSim,
  type Level,
  type LogEntry,
  type Sim,
  type Truck as TruckState,
} from "../demo/engine";

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink";

export default function DemoConsole() {
  const init = useScreenInit();
  const preset = typeof init.preset === "string" ? init.preset : undefined;
  const [sim, setSim] = useState<Sim>(() => presetSim(preset));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<1 | 4>(1);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setSim((s) => tick(s, 0.25 * speed)), 250);
    return () => clearInterval(id);
  }, [playing, speed]);

  const togglePlay = () => {
    if (!sim.started) setSim((s) => startCall(s));
    setPlaying((p) => !p);
  };
  const reset = () => {
    setPlaying(false);
    setSim(initialSim());
  };

  return (
    <div className="flex h-screen min-h-[840px] flex-col bg-night text-ink">
      <TopBar
        sim={sim}
        playing={playing}
        speed={speed}
        onSpeed={setSpeed}
        onPlay={togglePlay}
        onReset={reset}
      />
      <main className="flex min-h-0 flex-1 flex-col gap-4 p-5">
        <EscalationPanel sim={sim} onUpdate={setSim} />
        <div className="flex min-h-0 flex-1 gap-4">
          <Transcript sim={sim} />
          <div className="flex w-[440px] shrink-0 flex-col gap-4">
            <Controls sim={sim} onUpdate={setSim} />
            <EventLog log={sim.log} />
          </div>
        </div>
      </main>
    </div>
  );
}

/* ---------- Top bar ---------- */

function TopBar({
  sim,
  playing,
  speed,
  onSpeed,
  onPlay,
  onReset,
}: {
  sim: Sim;
  playing: boolean;
  speed: 1 | 4;
  onSpeed: (s: 1 | 4) => void;
  onPlay: () => void;
  onReset: () => void;
}) {
  const sinceRest = sim.t - sim.lastRestAt;
  return (
    <header className="flex h-[76px] shrink-0 items-center justify-between gap-8 border-b border-line bg-panel px-6">
      <div className="flex items-center gap-8">
        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-bold tracking-tight text-magenta">Khalasi</span>
          <span className="text-lg text-ink-muted">Demo console</span>
        </div>
        <div className="h-8 w-px bg-line" />
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-full bg-raised text-base font-semibold text-teal">
            RY
          </div>
          <div className="leading-tight">
            <div className="text-lg font-semibold">Raju Yadav</div>
            <div className="text-base text-ink-muted">NH-44 · Nagpur to Jhansi · Hindi</div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-right leading-tight">
          <div className="font-mono text-2xl font-medium tabular-nums">{clock(sim.t)}</div>
          <div className="text-base text-ink-muted">
            Started 7:00 pm · {hm(sinceRest)} since last rest
          </div>
        </div>
        <div className="h-8 w-px bg-line" />
        <div
          role="group"
          aria-label="Playback speed"
          className="flex rounded-control border border-line bg-night p-1"
        >
          {([1, 4] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={speed === v}
              onClick={() => onSpeed(v)}
              className={`h-9 w-14 rounded-md font-mono text-base font-medium ${focusRing} ${
                speed === v ? "bg-raised text-ink" : "text-ink-muted hover:text-ink"
              }`}
            >
              {v}x
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onReset}
          className={`flex h-11 items-center gap-2 rounded-control border border-line px-4 text-base font-medium text-ink-muted hover:border-line-strong hover:text-ink ${focusRing}`}
        >
          <RotateCcw size={18} strokeWidth={2} />
          Reset
        </button>
        <button
          type="button"
          onClick={onPlay}
          className={`flex h-11 min-w-[148px] items-center justify-center gap-2 rounded-control bg-ink px-5 text-lg font-semibold text-night hover:bg-ink-muted ${focusRing}`}
        >
          {playing ? <Pause size={20} strokeWidth={2} /> : sim.started ? <Play size={20} strokeWidth={2} /> : <PhoneCall size={20} strokeWidth={2} />}
          {playing ? "Pause" : sim.started ? "Resume" : "Start call"}
        </button>
      </div>
    </header>
  );
}

/* ---------- Escalation ---------- */

const levelText: Record<Level, string> = { green: "text-safe", amber: "text-warn", red: "text-danger" };

function EscalationPanel({ sim, onUpdate }: { sim: Sim; onUpdate: (fn: (s: Sim) => Sim) => void }) {
  const level = levelOf(sim);
  const label = stateLabel(sim);
  const elapsed = sim.esc ? sim.t - sim.esc.start : 0;
  const canAnswer = sim.mode === "escalating" || sim.mode === "alert";
  const canMarkSafe = sim.mode === "alert";

  return (
    <section
      aria-label="Escalation"
      className={`grid h-[188px] shrink-0 grid-cols-[360px_200px_1fr_220px] items-stretch rounded-panel border bg-panel ${
        level === "red" ? "border-danger/60" : "border-line"
      }`}
    >
      {/* Meter + state */}
      <div className="flex flex-col justify-between border-r border-line p-5">
        <div className="flex gap-1.5" aria-label={`Escalation level ${level}`}>
          <MeterSegment label="Green" on={level === "green"} tone="green" />
          <MeterSegment label="Amber" on={level === "amber"} tone="amber" />
          <MeterSegment label="Red" on={level === "red"} tone="red" />
        </div>
        <div>
          <div className={`text-3xl font-semibold tracking-tight ${levelText[level]}`}>{label.title}</div>
          <div className="mt-1 text-lg text-ink-muted">{label.detail}</div>
        </div>
        <div className="flex items-center gap-2 text-base text-ink-muted">
          <span>Sleep signs</span>
          <span className="font-mono font-semibold text-ink tabular-nums">{sim.signs}</span>
        </div>
      </div>

      {/* Silence timer */}
      <div className="flex flex-col justify-center border-r border-line px-6">
        <div className="text-lg text-ink-muted">
          {sim.esc?.kind === "unreachable" ? "Unreachable for" : "Silence"}
        </div>
        <div
          className={`font-mono text-6xl font-semibold tabular-nums ${
            sim.esc ? levelText[level] : "text-ink-faint"
          }`}
        >
          {mmss(elapsed)}
        </div>
      </div>

      {/* Milestone road */}
      <MilestoneRoad sim={sim} level={level} elapsed={elapsed} />

      {/* Resolve */}
      <div className="flex flex-col justify-center gap-3 border-l border-line p-5">
        <ActionButton
          icon={PhoneIncoming}
          label="Raju answers"
          disabled={!canAnswer}
          reason="Available while Khalasi is trying to reach Raju"
          onClick={() => onUpdate(rajuAnswers)}
        />
        <ActionButton
          icon={ShieldCheck}
          label="Sunita: He's safe"
          disabled={!canMarkSafe}
          reason="Available after Sunita is alerted"
          onClick={() => onUpdate(sunitaMarksSafe)}
        />
      </div>
    </section>
  );
}

function MeterSegment({ label, on, tone }: { label: string; on: boolean; tone: Level }) {
  const onClass =
    tone === "green" ? "bg-safe text-night" : tone === "amber" ? "bg-warn text-night" : "bg-danger text-night";
  return (
    <div
      className={`flex h-9 flex-1 items-center justify-center rounded-md text-base font-semibold ${
        on ? onClass : "bg-raised text-ink-faint"
      }`}
    >
      {label}
    </div>
  );
}

function MilestoneRoad({ sim, level, elapsed }: { sim: Sim; level: Level; elapsed: number }) {
  const pct = Math.min(1, elapsed / ALERT_AT);
  const active = !!sim.esc;
  const fill = level === "red" ? "bg-danger" : "bg-warn";
  const unreachable = sim.esc?.kind === "unreachable";

  return (
    <div className="relative px-14 pt-6" aria-label="Escalation steps">
      <div className="relative h-full">
        {/* Road */}
        <div className="absolute left-0 right-0 top-[30px] h-1.5 rounded-full bg-raised" />
        <div
          className={`absolute left-0 top-[30px] h-1.5 rounded-full ${active ? fill : "bg-transparent"}`}
          style={{ width: `${pct * 100}%` }}
        />
        {active && (
          <div
            className={`absolute top-[17px] -ml-4 grid size-8 place-items-center rounded-full bg-night ${levelText[level]}`}
            style={{ left: `${pct * 100}%` }}
            aria-hidden
          >
            <Truck size={20} strokeWidth={2} />
          </div>
        )}
        {/* Start */}
        <div className="absolute left-0 top-[58px] -ml-6 w-12 text-center">
          <div className="font-mono text-base text-ink-muted">0:00</div>
        </div>
        {MILESTONES.map((m) => {
          const reached = active && elapsed >= m.at;
          const skipped = unreachable && m.at === 15;
          const isRed = m.at >= 90;
          return (
            <Milestone
              key={m.at}
              left={(m.at / ALERT_AT) * 100}
              time={mmss(m.at)}
              label={skipped ? "Nudge skipped" : m.label}
              state={skipped ? "skipped" : reached ? (isRed ? "red" : "amber") : "upcoming"}
            />
          );
        })}
      </div>
    </div>
  );
}

// Signature: escalation steps drawn as NH kilometre stones.
function Milestone({
  left,
  time,
  label,
  state,
}: {
  left: number;
  time: string;
  label: string;
  state: "upcoming" | "amber" | "red" | "skipped";
}) {
  const cap =
    state === "amber" ? "bg-warn" : state === "red" ? "bg-danger" : state === "skipped" ? "bg-transparent" : "bg-line-strong";
  const body = state === "skipped" ? "border-dashed border-line-strong bg-transparent" : "border-line-strong bg-raised";
  const text = state === "upcoming" || state === "skipped" ? "text-ink-muted" : "text-ink";
  return (
    <div className="absolute top-0 -ml-14 flex w-28 flex-col items-center" style={{ left: `${left}%` }}>
      <div className={`flex h-[60px] w-12 flex-col overflow-hidden rounded-t-full border ${body}`}>
        <div className={`h-5 ${cap}`} />
        <div className={`grid flex-1 place-items-center font-mono text-base font-semibold ${text}`}>{time}</div>
      </div>
      <div className={`mt-2 text-center text-base leading-tight ${text}`}>{label}</div>
    </div>
  );
}

/* ---------- Transcript ---------- */

function Transcript({ sim }: { sim: Sim }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [sim.lines.length]);

  return (
    <section aria-label="Live call" className="flex min-w-0 flex-1 flex-col rounded-panel border border-line bg-panel">
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-line px-6">
        <h2 className="text-xl font-semibold">Live call</h2>
        <div className="flex items-center gap-2 text-base">
          {sim.onCall ? (
            <>
              <span className="size-2.5 rounded-full bg-safe" aria-hidden />
              <span>On call</span>
              <span className="font-mono text-ink-muted tabular-nums">{mmss(sim.t)}</span>
            </>
          ) : (
            <>
              <PhoneOff size={18} strokeWidth={2} className="text-ink-muted" />
              <span className="text-ink-muted">{sim.started ? "Call ended" : "No call yet"}</span>
            </>
          )}
        </div>
      </div>

      <div ref={ref} className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
        {sim.lines.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Phone size={32} strokeWidth={1.5} className="text-ink-faint" />
            <p className="text-xl font-medium">No call yet</p>
            <p className="text-lg text-ink-muted">Start call plays Raju's missed call at 12:10 am</p>
          </div>
        ) : (
          <ol className="flex flex-col">
            {sim.lines.map((l) => (
              <li
                key={l.id}
                className="grid animate-fade grid-cols-[112px_1fr] gap-4 border-b border-line/60 py-4 last:border-b-0 motion-reduce:animate-none"
              >
                <div className="pt-1">
                  <div className={`text-lg font-semibold ${l.speaker === "khalasi" ? "text-magenta" : "text-teal"}`}>
                    {l.speaker === "khalasi" ? "Khalasi" : "Raju"}
                  </div>
                  <div className="font-mono text-base text-ink-muted tabular-nums">{mmss(l.at)}</div>
                </div>
                <div className="min-w-0">
                  <p lang="hi" className="text-2xl font-medium leading-snug">
                    {l.hi}
                  </p>
                  <p className="mt-1 text-lg leading-snug text-ink-muted">{l.en}</p>
                  {l.flags && l.flags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {l.flags.map((f) => (
                        <span
                          key={f.label}
                          className="inline-flex items-center gap-1.5 rounded-md border border-warn/50 bg-warn-deep px-2.5 py-1 text-base text-warn"
                        >
                          <MessageCircleWarning size={16} strokeWidth={2} />
                          {f.label}
                          <span className="font-mono tabular-nums">· {mmss(f.at)}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

/* ---------- Controls ---------- */

const TRUCK_OPTIONS: { id: TruckState; label: string; icon: LucideIcon }[] = [
  { id: "moving", label: "Moving", icon: Truck },
  { id: "dhaba", label: "Stopped at dhaba", icon: Coffee },
  { id: "highway", label: "Stopped on highway", icon: CirclePause },
];

function Controls({ sim, onUpdate }: { sim: Sim; onUpdate: (fn: (s: Sim) => Sim) => void }) {
  const notStarted = !sim.started;
  const escalating = !!sim.esc;
  const dark = sim.mode === "darkBrief" || sim.mode === "darkStretch";

  const sims: { label: string; icon: LucideIcon; run: (s: Sim) => Sim; disabled: boolean; reason: string }[] = [
    {
      label: "Dark stretch ahead",
      icon: WifiOff,
      run: darkStretchAhead,
      disabled: notStarted || escalating || dark || !sim.onCall,
      reason: notStarted ? "Start the call first" : dark ? "Already in the dark stretch" : "Needs a live call",
    },
    {
      label: "Phone unreachable",
      icon: PhoneOff,
      run: phoneUnreachable,
      disabled: notStarted || escalating || sim.mode === "alert",
      reason: notStarted ? "Start the call first" : "Khalasi is already trying to reach Raju",
    },
    {
      label: "No answer",
      icon: PhoneMissed,
      run: noAnswer,
      disabled: notStarted || escalating || sim.mode === "alert" || !sim.onCall,
      reason: notStarted ? "Start the call first" : !sim.onCall ? "Needs a live call" : "Khalasi is already trying to reach Raju",
    },
    {
      label: "Driver says chup",
      icon: VolumeX,
      run: driverSaysChup,
      disabled: notStarted || escalating || !sim.onCall,
      reason: notStarted ? "Start the call first" : "Needs a live call",
    },
  ];

  return (
    <section aria-label="Controls" className="shrink-0 rounded-panel border border-line bg-panel p-5">
      <h2 className="text-lg font-semibold">Truck status</h2>
      <div role="radiogroup" aria-label="Truck status" className="mt-3 grid grid-cols-3 gap-2">
        {TRUCK_OPTIONS.map((o) => {
          const Icon = o.icon;
          const on = sim.truck === o.id;
          return (
            <button
              key={o.id}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => onUpdate((s) => setTruck(s, o.id))}
              className={`flex h-[84px] flex-col items-center justify-center gap-1.5 rounded-control border px-2 text-center text-base leading-tight ${focusRing} ${
                on ? "border-ink bg-raised font-semibold text-ink" : "border-line text-ink-muted hover:border-line-strong hover:text-ink"
              }`}
            >
              <Icon size={22} strokeWidth={2} />
              {o.label}
            </button>
          );
        })}
      </div>

      <h2 className="mt-5 text-lg font-semibold">Simulate</h2>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {sims.map((x) => (
          <ActionButton
            key={x.label}
            icon={x.icon}
            label={x.label}
            disabled={x.disabled}
            reason={x.reason}
            onClick={() => onUpdate(x.run)}
          />
        ))}
      </div>
    </section>
  );
}

function ActionButton({
  icon: Icon,
  label,
  disabled,
  reason,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  disabled: boolean;
  reason: string;
  onClick: () => void;
}) {
  return (
    <span title={disabled ? reason : undefined} className="block">
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className={`flex h-12 w-full items-center gap-2.5 rounded-control border border-line px-3 text-left text-base font-medium ${focusRing} enabled:text-ink enabled:hover:border-line-strong enabled:hover:bg-raised disabled:cursor-not-allowed disabled:text-ink-faint`}
      >
        <Icon size={20} strokeWidth={2} className="shrink-0" />
        {label}
      </button>
    </span>
  );
}

/* ---------- Event log ---------- */

const KIND_ICON: Record<LogEntry["kind"], LucideIcon> = {
  call: PhoneCall,
  stop: UtensilsCrossed,
  nudge: MessageCircleWarning,
  callback: PhoneMissed,
  alert: BellRing,
  schedule: CalendarClock,
  resolve: ShieldCheck,
  info: Info,
};
const TONE_TEXT: Record<LogEntry["tone"], string> = {
  neutral: "text-ink-muted",
  amber: "text-warn",
  red: "text-danger",
  green: "text-safe",
};

function EventLog({ log }: { log: LogEntry[] }) {
  const rows = [...log].reverse();
  return (
    <section aria-label="Event log" className="flex min-h-0 flex-1 flex-col rounded-panel border border-line bg-panel">
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-line px-5">
        <h2 className="text-lg font-semibold">Event log</h2>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 ? (
          <p className="px-5 py-6 text-base text-ink-muted">Nudges, call-backs and alerts show here</p>
        ) : (
          <ol>
            {rows.map((e) => {
              const Icon = KIND_ICON[e.kind];
              return (
                <LogRow key={e.id} red={e.tone === "red" && e.kind === "alert"}>
                  <Icon size={18} strokeWidth={2} className={`mt-0.5 shrink-0 ${TONE_TEXT[e.tone]}`} />
                  <div className="min-w-0 flex-1 text-base leading-snug">{e.text}</div>
                  <div className="shrink-0 font-mono text-sm text-ink-muted tabular-nums">{clock(e.at)}</div>
                </LogRow>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}

function LogRow({ red, children }: { red: boolean; children: ReactNode }) {
  return (
    <li
      className={`flex animate-fade items-start gap-3 border-b border-line/60 px-5 py-3 last:border-b-0 motion-reduce:animate-none ${
        red ? "bg-danger-deep" : ""
      }`}
    >
      {children}
    </li>
  );
}
