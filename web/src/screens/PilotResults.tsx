// Not in Figr: built plainly from design tokens. Simulated pilot results (rule 8: every
// synthetic number is labelled "Simulated"). Data comes from the seeded generator in ../pilot.
import type { ReactNode } from "react";
import { pilotData, pilotSummary, type Arm } from "../pilot/generate";
import { ARM_COLOR, ARM_LABEL, ChartPanel, GroupedBars, Legend, Lines, PartBars, SimChip, type Series } from "../pilot/charts";

const armSeries = (values: Record<Arm, number[]>): Series[] => [
  { name: ARM_LABEL.khalasi, color: ARM_COLOR.khalasi, values: values.khalasi },
  { name: ARM_LABEL.control, color: ARM_COLOR.control, values: values.control },
];

const signed = (v: number, unit = "") => `${v > 0 ? "+" : ""}${v}${unit}`;

export default function PilotResults() {
  const data = pilotData();
  const s = pilotSummary(data);
  const months = ["Weeks 1–4", "Weeks 5–8", "Weeks 9–12"];
  const nightSeries = armSeries(data.nightHours);
  const hbSeries = armSeries(data.harshBraking.perLakhKm);
  const crashSeries = armSeries(data.crashes.monthlyPerLakhKm);
  const dsSeries = armSeries(data.darkStretch.pct);
  const retentionSeries: Series[] = [
    { name: "Drivers still calling", color: ARM_COLOR.khalasi, values: data.retention.active },
  ];
  const faSeries: Series[] = [
    { name: "False alarms per family per month", color: ARM_COLOR.khalasi, values: data.falseAlarms.perFamilyPerMonth },
  ];

  return (
    <div className="min-h-screen bg-night text-ink">
      <header className="flex h-[76px] items-center justify-between gap-8 border-b border-line bg-panel px-6">
        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-bold tracking-tight text-magenta">Khalasi</span>
          <h1 className="text-lg text-ink-muted">Pilot results</h1>
          <span className="self-center">
            <SimChip />
          </span>
        </div>
        <p className="text-base text-ink-muted">100 trucks, random assignment by truck, 12 weeks, generated data</p>
      </header>

      <main className="mx-auto flex max-w-[1440px] flex-col gap-4 p-5">
        {/* Headline tiles */}
        <section aria-label="Headline numbers" className="grid grid-cols-4 gap-4">
          <StatTile
            label="Warnings that ended in a rest stop"
            value={`${s.warnings.pct}%`}
            sub={`${s.warnings.rested.toLocaleString("en-IN")} of ${s.warnings.issued.toLocaleString("en-IN")} warnings · Khalasi arm only`}
          />
          <StatTile
            label="Night driving hours / truck / week"
            value={`${s.nightHours.end.khalasi.toFixed(1)} h`}
            sub={`Khalasi W1 ${s.nightHours.start.khalasi.toFixed(1)} → W12 ${s.nightHours.end.khalasi.toFixed(1)} (${signed(s.nightHours.khalasiChangePct, "%")})`}
            compare={`Control W1 ${s.nightHours.start.control.toFixed(1)} → W12 ${s.nightHours.end.control.toFixed(1)} h`}
            note={s.nightHours.guardrailHeld ? "Guardrail held: did not rise" : "Guardrail breached: rose"}
            noteTone={s.nightHours.guardrailHeld ? "safe" : "danger"}
          />
          <StatTile
            label="Harsh braking / lakh km"
            value={s.harshBrakingPerLakhKm.khalasi.toFixed(1)}
            sub={`Khalasi · ${signed(s.harshBrakingPerLakhKm.diffPct, "%")} vs control`}
            compare={`Control ${s.harshBrakingPerLakhKm.control.toFixed(1)}`}
          />
          <StatTile
            label="Crashes / lakh km"
            value={s.crashesPerLakhKm.khalasi.toFixed(2)}
            sub={`Khalasi · ${s.crashesPerLakhKm.counts.khalasi} crashes in 12 weeks`}
            compare={`Control ${s.crashesPerLakhKm.control.toFixed(2)} · ${s.crashesPerLakhKm.counts.control} crashes`}
            note="Small counts: noisy"
            noteTone="warn"
          />
          <StatTile
            label="Promised stops kept"
            value={`${s.promisedStops.pct}%`}
            sub={`${s.promisedStops.kept.toLocaleString("en-IN")} of ${s.promisedStops.promised.toLocaleString("en-IN")} promised · Khalasi arm only`}
          />
          <StatTile
            label="False alarms / family / month"
            value={s.falseAlarmsPerFamilyPerMonth.toFixed(2)}
            sub={`${data.falseAlarms.families} families · Khalasi arm only`}
          />
          <StatTile
            label="Stops before a dark stretch"
            value={`${s.darkStretchStopPct.khalasi}%`}
            sub="Khalasi · share of approaches"
            compare={`Control ${s.darkStretchStopPct.control}%`}
          />
          <StatTile
            label="Drivers still calling, week 12"
            value={`${s.retention.week12} of ${s.retention.enrolled}`}
            sub={`${s.retention.pct}% of the Khalasi arm · at least one call that week`}
          />
        </section>

        {/* Guardrail */}
        <ChartPanel
          title="Guardrail: night driving hours per truck per week"
          legend={<Legend series={nightSeries} />}
          caption={
            <>
              <span className="font-semibold text-ink">Guardrail: night driving in the Khalasi arm must not rise.</span>{" "}
              Khalasi arm {s.nightHours.start.khalasi.toFixed(1)} h in week 1 to {s.nightHours.end.khalasi.toFixed(1)} h in week 12 (
              {signed(s.nightHours.khalasiChangePct, "%")}); control stays around {s.nightHours.start.control.toFixed(1)} h. Khalasi
              asks drivers to rest, so a rise would mean the calls are being used to push through the night. Generated data; the dashed
              line is the Khalasi week-1 level.
            </>
          }
        >
          <div className="flex items-start gap-8">
            <div className="min-w-0 flex-1">
              <Lines
                labels={data.weekLabels}
                series={nightSeries}
                ariaLabel={`Line chart of mean night driving hours per truck per week over 12 weeks. Khalasi falls from ${s.nightHours.start.khalasi.toFixed(1)} to ${s.nightHours.end.khalasi.toFixed(1)} hours; control stays near ${s.nightHours.start.control.toFixed(1)} hours. Simulated.`}
                yMin={0}
                yMax={24}
                unit=" h"
                format={(v) => v.toFixed(0)}
                labelFormat={(v) => v.toFixed(1)}
                refLine={{ value: s.nightHours.start.khalasi, label: "Khalasi week-1 level" }}
              />
            </div>
            <aside className="w-[380px] shrink-0 rounded-control border border-line bg-night p-4">
              <div className="text-base font-semibold uppercase tracking-wide text-ink-faint">Guardrail</div>
              <p className="mt-1 text-lg font-semibold leading-snug">Night driving hours in the Khalasi arm must not rise.</p>
              <dl className="mt-3 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-base tabular-nums">
                <dt className="text-ink-muted">Khalasi, week 1</dt>
                <dd className="font-mono text-right">{s.nightHours.start.khalasi.toFixed(1)} h</dd>
                <dt className="text-ink-muted">Khalasi, week 12</dt>
                <dd className="font-mono text-right">{s.nightHours.end.khalasi.toFixed(1)} h</dd>
                <dt className="text-ink-muted">Control, week 1 to 12</dt>
                <dd className="font-mono text-right">
                  {s.nightHours.start.control.toFixed(1)} to {s.nightHours.end.control.toFixed(1)} h
                </dd>
              </dl>
              <span
                className={`mt-3 inline-block rounded-md border px-2 py-0.5 text-sm font-medium ${
                  s.nightHours.guardrailHeld ? "border-safe/50 bg-safe-deep text-safe" : "border-danger/50 bg-danger-deep text-danger"
                }`}
              >
                {s.nightHours.guardrailHeld ? "Held: did not rise in any week" : "Breached: rose"}
              </span>
            </aside>
          </div>
        </ChartPanel>

        <div className="grid grid-cols-2 gap-4">
          <ChartPanel
            title="Harsh braking per lakh km, weekly"
            legend={<Legend series={hbSeries} />}
            caption={
              <>
                Over 12 weeks: Khalasi {s.harshBrakingPerLakhKm.khalasi.toFixed(1)}, control {s.harshBrakingPerLakhKm.control.toFixed(1)} events per
                lakh km ({signed(s.harshBrakingPerLakhKm.diffPct, "%")}). About {Math.round(data.lakhKm.khalasi.reduce((a, b) => a + b, 0))} lakh km per arm. Weekly bars bounce; read the
                12-week totals, not single weeks.
              </>
            }
          >
            <GroupedBars
              labels={data.weekLabels}
              series={hbSeries}
              ariaLabel={`Grouped bar chart of harsh braking events per lakh km by week for Khalasi and control. Twelve-week totals: Khalasi ${s.harshBrakingPerLakhKm.khalasi}, control ${s.harshBrakingPerLakhKm.control}. Simulated.`}
              format={(v) => v.toFixed(0)}
            />
          </ChartPanel>

          <ChartPanel
            title="Crashes per lakh km, 4-week blocks"
            legend={<Legend series={crashSeries} />}
            caption={
              <>
                {s.crashesPerLakhKm.counts.khalasi} crashes in the Khalasi arm and {s.crashesPerLakhKm.counts.control} in control across the whole pilot
                ({s.crashesPerLakhKm.khalasi.toFixed(2)} vs {s.crashesPerLakhKm.control.toFixed(2)} per lakh km). With counts this small the gap is
                within chance; weekly bars would be mostly zero, so blocks of 4 weeks are shown.
              </>
            }
          >
            <GroupedBars
              labels={months}
              series={crashSeries}
              ariaLabel={`Grouped bar chart of crashes per lakh km in three 4-week blocks for Khalasi and control. Totals: Khalasi ${s.crashesPerLakhKm.counts.khalasi} crashes, control ${s.crashesPerLakhKm.counts.control}. Simulated.`}
              format={(v) => v.toFixed(2)}
            />
          </ChartPanel>

          <ChartPanel
            title="Promised stops kept, weekly"
            legend={
              <Legend
                series={[
                  { name: "Kept", color: ARM_COLOR.khalasi, values: [] },
                  { name: "Promised", color: "var(--color-raised)", values: [], dashed: true },
                ]}
              />
            }
            caption={
              <>
                {s.promisedStops.kept.toLocaleString("en-IN")} of {s.promisedStops.promised.toLocaleString("en-IN")} promised stops kept ({s.promisedStops.pct}%)
                over 12 weeks. Khalasi arm only; a stop counts as kept if taken within 15 minutes of the promised time. Weekly counts fall as fewer
                drivers keep calling.
              </>
            }
          >
            <PartBars
              labels={data.weekLabels}
              part={data.promisedStops.kept}
              whole={data.promisedStops.promised}
              partName="Kept"
              wholeName="Promised"
              color={ARM_COLOR.khalasi}
              ariaLabel={`Bar chart of promised stops per week with the kept portion filled. Over 12 weeks ${s.promisedStops.kept} of ${s.promisedStops.promised} promised stops were kept, ${s.promisedStops.pct} percent. Simulated.`}
            />
          </ChartPanel>

          <ChartPanel
            title="False alarms per family per month"
            caption={
              <>
                {s.falseAlarmsPerFamilyPerMonth.toFixed(2)} false alarms per family per month on average across {data.falseAlarms.families} families
                (Khalasi arm only), {data.falseAlarms.falseAlarms.reduce((a, b) => a + b, 0)} false alarms out of{" "}
                {data.falseAlarms.alerts.reduce((a, b) => a + b, 0)} family alerts. A false alarm is one the contact marked as such on the alert page.
              </>
            }
          >
            <GroupedBars
              labels={months}
              series={faSeries}
              ariaLabel={`Bar chart of false alarms per family per month in three 4-week blocks: ${data.falseAlarms.perFamilyPerMonth.join(", ")}. Simulated.`}
              format={(v) => v.toFixed(2)}
              yMax={1}
            />
          </ChartPanel>

          <ChartPanel
            title="Stops before a dark stretch, weekly"
            legend={<Legend series={dsSeries} />}
            caption={
              <>
                Share of dark-stretch approaches where the truck stopped at a safe stop first: Khalasi {s.darkStretchStopPct.khalasi}%, control{" "}
                {s.darkStretchStopPct.control}% over 12 weeks. Both arms meet the same seeded stretches; only Khalasi drivers get the nudge before one.
              </>
            }
          >
            <GroupedBars
              labels={data.weekLabels}
              series={dsSeries}
              ariaLabel={`Grouped bar chart of the percentage of dark-stretch approaches with a stop beforehand, by week, for Khalasi and control. Twelve-week totals: Khalasi ${s.darkStretchStopPct.khalasi} percent, control ${s.darkStretchStopPct.control} percent. Simulated.`}
              unit="%"
              yMax={60}
              format={(v) => v.toFixed(0)}
            />
          </ChartPanel>

          <ChartPanel
            title="Drivers still calling each week"
            caption={
              <>
                {data.retention.active[0]} of {s.retention.enrolled} Khalasi-arm drivers took a call in week 1; {s.retention.week12} ({s.retention.pct}%) were
                still calling in week 12. Drivers who stop calling stay in the arm for night hours, braking and crash figures.
              </>
            }
          >
            <Lines
              labels={data.weekLabels}
              series={retentionSeries}
              ariaLabel={`Line chart of Khalasi-arm drivers with at least one call each week, from ${data.retention.active[0]} in week 1 to ${s.retention.week12} in week 12 out of ${s.retention.enrolled} enrolled. Simulated.`}
              yMin={0}
              yMax={s.retention.enrolled}
              format={(v) => v.toFixed(0)}
              area
            />
          </ChartPanel>
        </div>

        {/* How to read this */}
        <section aria-label="How to read this" className="rounded-panel border border-line bg-panel">
          <div className="flex h-14 items-center justify-between border-b border-line px-5">
            <h2 className="text-lg font-semibold">How to read this</h2>
            <SimChip small />
          </div>
          <div className="grid grid-cols-2 gap-8 px-5 py-5">
            <div>
              <h3 className="mb-3 text-base font-semibold uppercase tracking-wide text-ink-faint">Caveats</h3>
              <ul className="flex flex-col gap-2 text-base leading-snug text-ink-muted">
                {data.caveats.map((c) => (
                  <li key={c} className="flex gap-2">
                    <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-marigold" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 font-mono text-sm text-ink-faint">
                Generator: mulberry32, seed 0x{data.seed.toString(16)}, {data.trucks} trucks ({data.arms.khalasi} Khalasi / {data.arms.control} control), {data.weeks}{" "}
                weeks. Same numbers on every load.
              </p>
            </div>
            <div>
              <h3 className="mb-3 text-base font-semibold uppercase tracking-wide text-ink-faint">Metric definitions</h3>
              <dl className="flex flex-col gap-3 text-base leading-snug">
                {data.definitions.map((d) => (
                  <div key={d.metric}>
                    <dt className="font-semibold text-ink">{d.metric}</dt>
                    <dd className="text-ink-muted">{d.definition}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

/* ---------- Stat tile ---------- */

function StatTile({
  label,
  value,
  sub,
  compare,
  note,
  noteTone = "warn",
}: {
  label: string;
  value: string;
  sub: ReactNode;
  compare?: ReactNode;
  note?: string;
  noteTone?: "safe" | "warn" | "danger";
}) {
  const tone = {
    safe: "border-safe/50 bg-safe-deep text-safe",
    warn: "border-warn/50 bg-warn-deep text-warn",
    danger: "border-danger/50 bg-danger-deep text-danger",
  }[noteTone];
  return (
    <div className="flex flex-col gap-1.5 rounded-panel border border-line bg-panel p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="text-base leading-tight text-ink-muted">{label}</div>
        <SimChip small />
      </div>
      <div className="font-mono text-4xl font-semibold tabular-nums">{value}</div>
      <div className="text-base leading-snug tabular-nums text-ink-muted">{sub}</div>
      {compare && <div className="text-base leading-snug tabular-nums text-ink-faint">{compare}</div>}
      {note && <span className={`mt-1 self-start rounded-md border px-2 py-0.5 text-sm font-medium ${tone}`}>{note}</span>}
    </div>
  );
}
