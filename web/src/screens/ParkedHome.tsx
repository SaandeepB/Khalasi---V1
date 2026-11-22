// Not in Figr: built plainly from design tokens
// Parked home (/home). Mobile web, Hindi first with English below (rule 9). Shown while the truck is parked.
// Trip values and the next stop come from a simulated truck status and are labelled "Simulated" (rule 8).
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeftRight, Clock, Coffee, MapPin, Phone, Smartphone, Truck } from "lucide-react";

// Placeholder: the real Khalasi number comes from the backend. Never commit a real number.
const KHALASI_NUMBER = "+91 00000 00000";
const KHALASI_TEL = "tel:+910000000000";

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink";

// Simulated trip for the demo driver.
const TRIP = {
  driver: "Raju Yadav",
  initials: "RY",
  truck: "MH 12 AB 1234",
  route: "NH-44 · Nagpur → Jhansi",
  started: { hi: "raat 7:00 baje", en: "7:00 pm IST" },
  lastRest: { hi: "Sharma dhaba", en: "Sharma dhaba" },
  // Hours since last rest, counted live from this simulated value at page load.
  sinceRestMinutesAtLoad: 2 * 60 + 10,
};

// Rule 3: the only stop named is the one returned by the (simulated) truck_status tool.
const NEXT_STOP = {
  hi: "Apna Ghar (demo), 8 km aage",
  en: "Apna Ghar (demo), 8 km ahead",
};

const IST_TIME = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

function useNow() {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function sinceRest(ms: number) {
  const total = Math.max(0, Math.floor(ms / 60000));
  const h = Math.floor(total / 60);
  const m = total % 60;
  return {
    hi: `${h} ghante ${m} minute`,
    en: `${h}h ${String(m).padStart(2, "0")}m`,
  };
}

export default function ParkedHome() {
  const now = useNow();
  const lastRestAt = useMemo(() => Date.now() - TRIP.sinceRestMinutesAtLoad * 60000, []);
  const rest = sinceRest(now - lastRestAt);

  return (
    <div className="min-h-screen bg-night text-ink">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col gap-4 px-4 py-5">
        <header className="flex items-center justify-between">
          <span className="text-2xl font-bold tracking-tight text-magenta">Khalasi</span>
          <span className="rounded-md border border-warn/50 bg-warn-deep px-2.5 py-1 text-sm font-medium text-warn">
            Simulated
          </span>
        </header>

        {/* Parked status */}
        <section
          aria-label="Truck status"
          className="flex items-center gap-3 rounded-panel border border-safe/60 bg-safe-deep px-5 py-4"
        >
          <Truck size={22} strokeWidth={2} className="shrink-0 text-safe" />
          <div className="min-w-0 leading-tight">
            <div lang="hi" className="text-xl font-semibold text-safe">
              Gaadi ruki hui hai
            </div>
            <div className="text-base text-ink-muted">Truck is parked · {TRIP.route}</div>
          </div>
          <span className="ml-auto shrink-0 text-sm text-ink-faint">Simulated</span>
        </section>

        {/* Trip clock */}
        <section aria-label="Trip clock" className="rounded-panel border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink-muted">
              <span lang="hi">Trip ki ghadi</span>
              <span className="text-ink-faint"> · Trip clock</span>
            </h2>
            <span className="text-sm text-ink-faint">IST · Simulated</span>
          </div>
          <ul className="mt-3 flex flex-col divide-y divide-line/60">
            <InfoRow icon={Truck} hi="Trip shuru" en="Trip started" valueHi={TRIP.started.hi} valueEn={TRIP.started.en} />
            <InfoRow icon={Clock} hi="Abhi" en="Time now" valueHi={IST_TIME.format(new Date(now))} valueEn="IST" mono />
            <InfoRow
              icon={Coffee}
              hi="Aakhri aaram ke baad"
              en="Since last rest"
              valueHi={rest.hi}
              valueEn={`${rest.en} · last rest at ${TRIP.lastRest.en}`}
              tone="amber"
            />
          </ul>
        </section>

        {/* Driver today */}
        <section aria-label="Driver today" className="rounded-panel border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink-muted">
              <span lang="hi">Aaj ka driver</span>
              <span className="text-ink-faint"> · Driver today</span>
            </h2>
            <span className="font-mono text-sm text-ink-faint">{TRIP.truck}</span>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <div className="grid size-12 shrink-0 place-items-center rounded-full bg-raised text-lg font-semibold text-teal">
              {TRIP.initials}
            </div>
            <div className="min-w-0 leading-tight">
              <div className="text-xl font-semibold">{TRIP.driver}</div>
              <div lang="hi" className="text-lg">
                Aaj gaadi aap chala rahe ho
              </div>
              <div className="text-sm text-ink-muted">You're driving today</div>
            </div>
          </div>
          {/* Present but inert in the demo: driver swap (R13) is handled by the backend. */}
          <button
            type="button"
            title="Demo: does nothing"
            className={`mt-3 inline-flex items-center gap-2 text-base text-ink-muted hover:text-ink ${focusRing}`}
          >
            <ArrowLeftRight size={16} strokeWidth={2} />
            <span lang="hi" className="underline underline-offset-4">
              Driver badlein
            </span>
            <span className="text-sm text-ink-faint">· Switch driver</span>
          </button>
        </section>

        {/* Next safe stop */}
        <section aria-label="Next safe stop" className="rounded-panel border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink-muted">
              <span lang="hi">Agla surakshit stop</span>
              <span className="text-ink-faint"> · Next safe stop</span>
            </h2>
            <span className="text-sm text-ink-faint">Truck status · Simulated</span>
          </div>
          <div className="mt-3 flex items-start gap-3">
            <MapPin size={22} strokeWidth={2} className="mt-1 shrink-0 text-marigold" />
            <div className="leading-tight">
              <div lang="hi" className="text-2xl font-semibold">
                {NEXT_STOP.hi}
              </div>
              <div className="mt-0.5 text-base text-ink-muted">{NEXT_STOP.en}</div>
            </div>
          </div>
        </section>

        {/* Call Khalasi */}
        <section aria-label="Call Khalasi" className="flex flex-col gap-2">
          <a
            href={KHALASI_TEL}
            className={`flex h-20 items-center justify-center gap-4 rounded-control bg-ink px-5 text-night hover:bg-ink-muted ${focusRing}`}
          >
            <Phone size={26} strokeWidth={2} />
            <span className="flex flex-col items-center leading-tight">
              <span lang="hi" className="text-2xl font-semibold">
                Khalasi ko call karein
              </span>
              <span className="text-base opacity-80">Call Khalasi</span>
            </span>
          </a>
          <p className="text-center font-mono text-sm text-ink-faint tabular-nums">
            {KHALASI_NUMBER} · demo number
          </p>
        </section>

        {/* Hands-free note */}
        <section
          aria-label="Hands-free note"
          className="flex items-start gap-3 rounded-panel border border-warn/50 bg-warn-deep px-5 py-4"
        >
          <Smartphone size={22} strokeWidth={2} className="mt-1 shrink-0 text-warn" />
          <div className="leading-tight">
            <p lang="hi" className="text-lg font-semibold text-warn">
              Gaadi chalate hue phone haath mein na lein
            </p>
            <p className="mt-0.5 text-base text-ink-muted">Don't hold the phone while driving</p>
          </div>
        </section>

        <footer className="mt-2 flex flex-col gap-1 text-sm text-ink-faint">
          <p lang="hi">Jagah sirf emergency mein, sirf aapke sampark ke saath share hoti hai.</p>
          <p>Location is shared only in an emergency, and only with your contact.</p>
          <p className="mt-2 flex items-center justify-between font-mono">
            <span>Home · Simulated · Times in IST</span>
            <Link to="/setup" className="underline underline-offset-4 hover:text-ink">
              Setup
            </Link>
          </p>
        </footer>
      </div>
    </div>
  );
}

function InfoRow({
  icon: Icon,
  hi,
  en,
  valueHi,
  valueEn,
  tone = "neutral",
  mono = false,
}: {
  icon: typeof Clock;
  hi: string;
  en: string;
  valueHi: string;
  valueEn: string;
  tone?: "neutral" | "amber";
  mono?: boolean;
}) {
  return (
    <li className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
      <div className="flex items-start gap-3">
        <Icon size={20} strokeWidth={2} className={`mt-1 shrink-0 ${tone === "amber" ? "text-warn" : "text-ink-muted"}`} />
        <div className="leading-tight">
          <div lang="hi" className="text-lg font-medium">
            {hi}
          </div>
          <div className="text-sm text-ink-muted">{en}</div>
        </div>
      </div>
      <div className="shrink-0 text-right leading-tight">
        <div lang="hi" className={`text-xl font-semibold tabular-nums ${mono ? "font-mono" : ""}`}>
          {valueHi}
        </div>
        <div className="text-sm text-ink-muted">{valueEn}</div>
      </div>
    </li>
  );
}
