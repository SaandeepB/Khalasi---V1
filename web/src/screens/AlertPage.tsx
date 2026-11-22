// Not in Figr: built plainly from design tokens
// Family alert page (/a/:token). Mobile web, Hindi first with English below each line.
// All data here is demo data for the simulated driver and is labelled "Simulated" (rule 8).
import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { BellRing, Clock, MapPin, Phone, ShieldCheck, Siren, Truck } from "lucide-react";

type Reason = "not_answering" | "unreachable";

// Placeholder: the real driver number comes from the backend with the alert token.
const RAJU_TEL = "tel:+910000000000";
const EMERGENCY_TEL = "tel:112";

const HEADLINE: Record<Reason, { hi: string; en: string }> = {
  not_answering: {
    hi: "Raju ji dhai minute se jawab nahi de rahe",
    en: "Raju hasn't answered for 2½ minutes",
  },
  unreachable: {
    hi: "Raju ji ka phone nahi lag raha. Shayad network nahi hai.",
    en: "Raju's phone is unreachable. He may be in a no-network stretch.",
  },
};

// Simulated last-known data for the demo driver.
const LAST_KNOWN = {
  place: { hi: "NH-44, Sagar ke paas", en: "NH-44, near Sagar" },
  time: { hi: "raat 12:40", en: "12:40 am IST" },
};

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink";

export default function AlertPage() {
  const { token } = useParams();
  const [params] = useSearchParams();
  const reason: Reason = params.get("reason") === "unreachable" ? "unreachable" : "not_answering";
  // Optional `?truck=stopped`; default is moving (fail safe, rule 2).
  const moving = params.get("truck") !== "stopped";
  // Demo only: ?tel=+91XXXXXXXXXX dials the teammate playing Raju. Never commit a real number.
  const telParam = params.get("tel");
  const rajuTel = telParam && /^\+?[0-9]{6,15}$/.test(telParam) ? `tel:${telParam}` : RAJU_TEL;
  const [safe, setSafe] = useState(false);
  const [falseAlarm, setFalseAlarm] = useState<"yes" | "no" | null>(null);

  const headline = HEADLINE[reason];

  return (
    <div className="min-h-screen bg-night text-ink">
      <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 py-5">
        {/* Header */}
        <header className="flex items-center justify-between">
          <span className="text-2xl font-bold tracking-tight text-magenta">Khalasi</span>
          <span className="rounded-md border border-warn/50 bg-warn-deep px-2.5 py-1 text-sm font-medium text-warn">
            Simulated
          </span>
        </header>

        {/* Headline */}
        <section
          aria-live="polite"
          className={`rounded-panel border p-5 ${
            safe ? "border-safe/60 bg-safe-deep" : "border-danger/60 bg-danger-deep"
          }`}
        >
          <div className={`flex items-center gap-2 text-base font-semibold ${safe ? "text-safe" : "text-danger"}`}>
            {safe ? <ShieldCheck size={20} strokeWidth={2} /> : <BellRing size={20} strokeWidth={2} />}
            {safe ? (
              <span lang="hi">Theek hain · Marked safe</span>
            ) : (
              <span>Khalasi alert</span>
            )}
          </div>
          <h1 lang="hi" className="mt-3 text-2xl font-semibold leading-snug">
            {headline.hi}
          </h1>
          <p className="mt-2 text-lg leading-snug text-ink-muted">{headline.en}</p>
        </section>

        {/* Last known location */}
        <section aria-label="Last known location" className="rounded-panel border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink-muted">
              <span lang="hi">Aakhri jaankari</span>
              <span className="text-ink-faint"> · Last known</span>
            </h2>
            <span className="text-sm text-ink-faint">Simulated</span>
          </div>
          <ul className="mt-3 flex flex-col divide-y divide-line/60">
            <InfoRow icon={MapPin} hi={LAST_KNOWN.place.hi} en={LAST_KNOWN.place.en} />
            <InfoRow icon={Clock} hi={LAST_KNOWN.time.hi} en={LAST_KNOWN.time.en} />
            <InfoRow
              icon={Truck}
              hi={moving ? "Truck chal raha hai" : "Truck ruka hua hai"}
              en={moving ? "Truck is moving" : "Truck is stopped"}
              tone={moving ? "amber" : "neutral"}
            />
          </ul>
        </section>

        {/* Actions */}
        <section aria-label="Actions" className="flex flex-col gap-3">
          <a
            href={rajuTel}
            className={`flex h-16 items-center justify-center gap-3 rounded-control bg-ink px-5 text-night hover:bg-ink-muted ${focusRing}`}
          >
            <Phone size={22} strokeWidth={2} />
            <TwoLine hi="Raju ko phone karein" en="Call Raju" />
          </a>
          <a
            href={EMERGENCY_TEL}
            className={`flex h-16 items-center justify-center gap-3 rounded-control border border-danger/60 bg-danger-deep px-5 text-danger hover:border-danger ${focusRing}`}
          >
            <Siren size={22} strokeWidth={2} />
            <TwoLine hi="112 par call karein" en="Call 112" />
          </a>
          {!safe && (
            <button
              type="button"
              onClick={() => setSafe(true)}
              className={`flex h-16 items-center justify-center gap-3 rounded-control border border-safe/60 bg-safe-deep px-5 text-safe hover:border-safe ${focusRing}`}
            >
              <ShieldCheck size={22} strokeWidth={2} />
              <TwoLine hi="Woh theek hain" en="He's safe" />
            </button>
          )}
        </section>

        {/* False alarm follow-up */}
        {safe && (
          <section aria-label="False alarm" className="animate-fade rounded-panel border border-line bg-panel p-5 motion-reduce:animate-none">
            {falseAlarm === null ? (
              <>
                <p lang="hi" className="text-xl font-semibold leading-snug">
                  Kya yeh galat alarm tha?
                </p>
                <p className="mt-1 text-base text-ink-muted">Was this a false alarm?</p>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setFalseAlarm("yes")}
                    className={`flex h-14 items-center justify-center rounded-control border border-line bg-raised text-ink hover:border-line-strong ${focusRing}`}
                  >
                    <TwoLine hi="Haan" en="Yes" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setFalseAlarm("no")}
                    className={`flex h-14 items-center justify-center rounded-control border border-line bg-raised text-ink hover:border-line-strong ${focusRing}`}
                  >
                    <TwoLine hi="Nahi" en="No" />
                  </button>
                </div>
              </>
            ) : (
              <>
                <p lang="hi" className="text-xl font-semibold leading-snug text-safe">
                  Dhanyavaad. Khalasi ab Raju ji ko phone karega.
                </p>
                <p className="mt-1 text-base text-ink-muted">Thank you. Khalasi will call Raju back now.</p>
              </>
            )}
          </section>
        )}

        <footer className="mt-2 flex flex-col gap-1 text-sm text-ink-faint">
          <p lang="hi">Jagah sirf emergency mein, sirf aapke saath share hoti hai.</p>
          <p>Location is shared only in an emergency, and only with you.</p>
          <p className="mt-2 font-mono">Alert · {token ?? "demo"} · Simulated</p>
        </footer>
      </div>
    </div>
  );
}

function TwoLine({ hi, en }: { hi: string; en: string }) {
  return (
    <span className="flex flex-col items-center leading-tight">
      <span lang="hi" className="text-lg font-semibold">
        {hi}
      </span>
      <span className="text-sm opacity-80">{en}</span>
    </span>
  );
}

function InfoRow({
  icon: Icon,
  hi,
  en,
  tone = "neutral",
}: {
  icon: typeof MapPin;
  hi: string;
  en: string;
  tone?: "neutral" | "amber";
}) {
  return (
    <li className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
      <Icon size={20} strokeWidth={2} className={`mt-1 shrink-0 ${tone === "amber" ? "text-warn" : "text-ink-muted"}`} />
      <div className="min-w-0 leading-tight">
        <div lang="hi" className="text-xl font-medium">
          {hi}
        </div>
        <div className="mt-0.5 text-base text-ink-muted">{en}</div>
      </div>
    </li>
  );
}
