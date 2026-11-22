// Simulated pilot data for /pilot. Everything here is synthetic (rule 8: shown as "Simulated").
// Design: one seeded PRNG (mulberry32) drives a per-truck, per-week simulation of 100 trucks
// assigned at random by truck to Khalasi or control for 12 weeks. Khalasi-only behaviours
// (warnings, promised stops, alerts) apply only to drivers still calling that week; the arm
// totals are intention-to-treat. Effects are modest and gradual by construction.

export const DEFAULT_SEED = 0x4b48_4c53; // "KHLS"
export const WEEKS = 12;
export const TRUCKS = 100;

export type Arm = "khalasi" | "control";
export type ArmValue = Record<Arm, number>;
export type ArmWeekly = Record<Arm, number[]>;

export type PilotData = {
  seed: number;
  weeks: number;
  trucks: number;
  arms: ArmValue;
  weekLabels: string[];
  /** Lakh km driven per arm per week. */
  lakhKm: ArmWeekly;
  /** Mean night driving hours per truck per week. Guardrail: Khalasi must not rise. */
  nightHours: ArmWeekly;
  harshBraking: { counts: ArmWeekly; perLakhKm: ArmWeekly; totals: ArmValue; totalPerLakhKm: ArmValue };
  crashes: {
    counts: ArmWeekly;
    /** Three 4-week blocks, per lakh km. Weekly counts are mostly 0 or 1, so weeks are not charted. */
    monthlyPerLakhKm: ArmWeekly;
    totals: ArmValue;
    totalPerLakhKm: ArmValue;
  };
  /** Khalasi arm only. */
  warnings: { issued: number[]; rested: number[]; totalIssued: number; totalRested: number; pct: number };
  /** Khalasi arm only. */
  promisedStops: { promised: number[]; kept: number[]; totalPromised: number; totalKept: number; pct: number };
  /** Khalasi arm only. One family contact per truck. */
  falseAlarms: {
    alerts: number[];
    falseAlarms: number[];
    families: number;
    perFamilyPerMonth: number[];
    overallPerFamilyPerMonth: number;
  };
  darkStretch: { approaches: ArmWeekly; stops: ArmWeekly; pct: ArmWeekly; totalPct: ArmValue };
  /** Khalasi arm only: drivers with at least one call that week. */
  retention: { enrolled: number; active: number[]; week12Pct: number };
  caveats: string[];
  definitions: { metric: string; definition: string }[];
};

export type PilotSummary = {
  trucks: number;
  weeks: number;
  arms: ArmValue;
  warnings: { issued: number; rested: number; pct: number };
  nightHours: { start: ArmValue; end: ArmValue; khalasiChangePct: number; guardrailHeld: boolean };
  harshBrakingPerLakhKm: ArmValue & { diffPct: number };
  crashesPerLakhKm: ArmValue & { counts: ArmValue };
  promisedStops: { promised: number; kept: number; pct: number };
  falseAlarmsPerFamilyPerMonth: number;
  darkStretchStopPct: ArmValue;
  retention: { enrolled: number; week12: number; pct: number };
};

/* ---------- PRNG and samplers ---------- */

export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Rng = () => number;

function poisson(rng: Rng, lambda: number): number {
  if (lambda <= 0) return 0;
  const limit = Math.exp(-lambda);
  let k = 0;
  let p = 1;
  do {
    k += 1;
    p *= rng();
  } while (p > limit);
  return k - 1;
}

function binomial(rng: Rng, n: number, p: number): number {
  let k = 0;
  for (let i = 0; i < n; i++) if (rng() < p) k += 1;
  return k;
}

function normal(rng: Rng): number {
  const u = 1 - rng();
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const zeros = () => Array.from({ length: WEEKS }, () => 0);
const armWeekly = (): ArmWeekly => ({ khalasi: zeros(), control: zeros() });
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
const round = (v: number, d = 1) => Math.round(v * 10 ** d) / 10 ** d;
const pct = (num: number, den: number) => (den > 0 ? round((100 * num) / den, 0) : 0);
const ARMS: Arm[] = ["khalasi", "control"];

/* ---------- Generator ---------- */

export function generatePilot(seed: number = DEFAULT_SEED): PilotData {
  const rng = mulberry32(seed);

  // Random assignment by truck, about 50/50.
  const trucks = Array.from({ length: TRUCKS }, (_, i) => ({
    id: i,
    arm: (rng() < 0.5 ? "khalasi" : "control") as Arm,
    nightBase: clamp(18 + 3 * normal(rng), 8, 30),
    active: true, // Khalasi arm: still calling. Starts true, may churn.
  }));
  const arms: ArmValue = {
    khalasi: trucks.filter((t) => t.arm === "khalasi").length,
    control: trucks.filter((t) => t.arm === "control").length,
  };

  const lakhKm = armWeekly();
  const nightRaw: Record<Arm, number[][]> = { khalasi: [], control: [] }; // [week][truck]
  const harshCounts = armWeekly();
  const crashCounts = armWeekly();
  const warningsIssued = zeros();
  const warningsRested = zeros();
  const promised = zeros();
  const kept = zeros();
  const alerts = zeros();
  const falseAlarms = zeros();
  const approaches = armWeekly();
  const dsStops = armWeekly();
  const active = zeros();

  // Week-1 take-up: a few enrolled drivers never take the first call.
  for (const t of trucks) if (t.arm === "khalasi" && rng() < 0.06) t.active = false;

  for (let w = 0; w < WEEKS; w++) {
    const f = w / (WEEKS - 1); // 0 -> 1 across the pilot
    nightRaw.khalasi.push([]);
    nightRaw.control.push([]);

    for (const t of trucks) {
      const arm = t.arm;
      const treated = arm === "khalasi" && t.active;

      const km = clamp(2200 + 450 * normal(rng), 800, 3600);
      const lk = km / 100_000;
      lakhKm[arm][w] += lk;

      // Night hours: raw noise around each truck's baseline; the Khalasi trend is applied below.
      nightRaw[arm][w].push(clamp(t.nightBase + 1.5 * normal(rng), 0, 40));

      // Harsh braking: control flat at ~42 per lakh km; Khalasi eases to ~36 by week 12.
      const hbRate = arm === "khalasi" ? 42 * (1 - 0.14 * f) : 42;
      harshCounts[arm][w] += poisson(rng, hbRate * lk);

      // Crashes: rare. Control ~0.42 per lakh km; Khalasi ~15% lower. Single-digit totals.
      const crRate = arm === "khalasi" ? 0.42 * 0.85 : 0.42;
      crashCounts[arm][w] += poisson(rng, crRate * lk);

      // Dark stretches: both arms meet them; only treated drivers get the pre-stretch nudge.
      const ap = poisson(rng, 2.8);
      const stopP = treated ? 0.28 + 0.14 * f : 0.28;
      approaches[arm][w] += ap;
      dsStops[arm][w] += binomial(rng, ap, stopP);

      if (arm === "khalasi" && t.active) {
        active[w] += 1;
        const issued = poisson(rng, 3.6);
        warningsIssued[w] += issued;
        warningsRested[w] += binomial(rng, issued, 0.52 + 0.08 * f);

        const pr = poisson(rng, 2.2);
        promised[w] += pr;
        kept[w] += binomial(rng, pr, 0.7 + 0.07 * f);

        const al = poisson(rng, 0.3);
        alerts[w] += al;
        falseAlarms[w] += binomial(rng, al, 0.5 - 0.1 * f);

        // Churn: stickier as weeks pass; no return once a driver stops calling.
        if (rng() > 0.955 + 0.03 * f) t.active = false;
      }
    }
  }

  // Night hours per truck per week. Khalasi arm: pin the weekly mean to a non-increasing path
  // (week 1 level, easing ~3.5% by week 12) so the guardrail holds by construction. Control: raw.
  const nightHours = armWeekly();
  for (const arm of ARMS) {
    const means = nightRaw[arm].map((vals) => sum(vals) / vals.length);
    for (let w = 0; w < WEEKS; w++) {
      nightHours[arm][w] =
        arm === "khalasi" ? round(means[0] * (1 - 0.035 * (w / (WEEKS - 1))), 2) : round(means[w], 2);
    }
  }

  const perLakh = (counts: ArmWeekly): ArmWeekly => ({
    khalasi: counts.khalasi.map((c, w) => round(c / lakhKm.khalasi[w], 1)),
    control: counts.control.map((c, w) => round(c / lakhKm.control[w], 1)),
  });
  const totals = (counts: ArmWeekly): ArmValue => ({ khalasi: sum(counts.khalasi), control: sum(counts.control) });
  const totalPerLakh = (counts: ArmWeekly, d = 1): ArmValue => ({
    khalasi: round(sum(counts.khalasi) / sum(lakhKm.khalasi), d),
    control: round(sum(counts.control) / sum(lakhKm.control), d),
  });
  const monthly = (counts: number[], km: number[]) =>
    [0, 1, 2].map((m) => {
      const c = sum(counts.slice(m * 4, m * 4 + 4));
      const k = sum(km.slice(m * 4, m * 4 + 4));
      return round(c / k, 2);
    });

  const families = arms.khalasi;
  const perFamilyPerMonth = [0, 1, 2].map((m) => round(sum(falseAlarms.slice(m * 4, m * 4 + 4)) / families, 2));

  const pctSeries = (num: number[], den: number[]) => num.map((n, i) => pct(n, den[i]));

  return {
    seed,
    weeks: WEEKS,
    trucks: TRUCKS,
    arms,
    weekLabels: Array.from({ length: WEEKS }, (_, i) => `W${i + 1}`),
    lakhKm: { khalasi: lakhKm.khalasi.map((v) => round(v, 2)), control: lakhKm.control.map((v) => round(v, 2)) },
    nightHours,
    harshBraking: {
      counts: harshCounts,
      perLakhKm: perLakh(harshCounts),
      totals: totals(harshCounts),
      totalPerLakhKm: totalPerLakh(harshCounts),
    },
    crashes: {
      counts: crashCounts,
      monthlyPerLakhKm: {
        khalasi: monthly(crashCounts.khalasi, lakhKm.khalasi),
        control: monthly(crashCounts.control, lakhKm.control),
      },
      totals: totals(crashCounts),
      totalPerLakhKm: totalPerLakh(crashCounts, 2),
    },
    warnings: {
      issued: warningsIssued,
      rested: warningsRested,
      totalIssued: sum(warningsIssued),
      totalRested: sum(warningsRested),
      pct: pct(sum(warningsRested), sum(warningsIssued)),
    },
    promisedStops: {
      promised,
      kept,
      totalPromised: sum(promised),
      totalKept: sum(kept),
      pct: pct(sum(kept), sum(promised)),
    },
    falseAlarms: {
      alerts,
      falseAlarms,
      families,
      perFamilyPerMonth,
      overallPerFamilyPerMonth: round(sum(falseAlarms) / families / 3, 2),
    },
    darkStretch: {
      approaches,
      stops: dsStops,
      pct: { khalasi: pctSeries(dsStops.khalasi, approaches.khalasi), control: pctSeries(dsStops.control, approaches.control) },
      totalPct: {
        khalasi: pct(sum(dsStops.khalasi), sum(approaches.khalasi)),
        control: pct(sum(dsStops.control), sum(approaches.control)),
      },
    },
    retention: { enrolled: arms.khalasi, active, week12Pct: pct(active[WEEKS - 1], arms.khalasi) },
    caveats: [
      "Simulated. Every number on this page comes from a seeded random generator, not from trucks on the road.",
      "Assignment is random by truck (about 50/50), not by driver or route. Drivers who swap trucks blur the two arms.",
      "12 weeks is short. Seasons, monsoon and festival traffic are not modelled.",
      "Crash counts are single digits per arm, so crashes per lakh km are noisy. Do not read the crash gap as evidence.",
      "Warnings, promised stops, false alarms and retention exist only in the Khalasi arm; they have no control comparison.",
      "Effects are modelled as modest and gradual on purpose. A real pilot could show no effect.",
    ],
    definitions: [
      { metric: "Warnings that ended in a rest stop", definition: "Share of Khalasi fatigue or dark-stretch warnings followed by a stop of 20 minutes or more within 45 minutes. Khalasi arm only." },
      { metric: "Night driving hours", definition: "Mean hours per truck per week driven between 22:00 and 05:00 IST. Guardrail: the Khalasi arm must not rise above its week-1 level." },
      { metric: "Harsh braking per lakh km", definition: "Telematics harsh-braking events divided by lakh (100,000) km driven, per arm." },
      { metric: "Crashes per lakh km", definition: "Reported crashes of any severity divided by lakh km driven, per arm, in 4-week blocks." },
      { metric: "Promised stops kept", definition: "Stops the driver promised to Khalasi on a call that were taken within 15 minutes of the promised time. Count and percentage. Khalasi arm only." },
      { metric: "False alarms per family per month", definition: "Family alerts the contact marked as a false alarm, divided by the number of families (one per Khalasi truck), per 4-week block." },
      { metric: "Stops before a dark stretch", definition: "Share of approaches to a seeded dark stretch where the truck stopped at a safe stop before entering it, per arm." },
      { metric: "Drivers still calling", definition: "Khalasi-arm drivers with at least one answered Khalasi call in the week." },
    ],
  };
}

let cached: PilotData | undefined;

/** Default simulated pilot (fixed seed), generated once. */
export function pilotData(): PilotData {
  if (!cached) cached = generatePilot(DEFAULT_SEED);
  return cached;
}

export function pilotSummary(data: PilotData = pilotData()): PilotSummary {
  const last = data.weeks - 1;
  const nh = data.nightHours;
  const guardrailHeld = nh.khalasi.every((v, i) => i === 0 || v <= nh.khalasi[i - 1] + 1e-9);
  const hb = data.harshBraking.totalPerLakhKm;
  return {
    trucks: data.trucks,
    weeks: data.weeks,
    arms: data.arms,
    warnings: { issued: data.warnings.totalIssued, rested: data.warnings.totalRested, pct: data.warnings.pct },
    nightHours: {
      start: { khalasi: nh.khalasi[0], control: nh.control[0] },
      end: { khalasi: nh.khalasi[last], control: nh.control[last] },
      khalasiChangePct: round((100 * (nh.khalasi[last] - nh.khalasi[0])) / nh.khalasi[0], 1),
      guardrailHeld,
    },
    harshBrakingPerLakhKm: { ...hb, diffPct: round((100 * (hb.khalasi - hb.control)) / hb.control, 0) },
    crashesPerLakhKm: { ...data.crashes.totalPerLakhKm, counts: data.crashes.totals },
    promisedStops: {
      promised: data.promisedStops.totalPromised,
      kept: data.promisedStops.totalKept,
      pct: data.promisedStops.pct,
    },
    falseAlarmsPerFamilyPerMonth: data.falseAlarms.overallPerFamilyPerMonth,
    darkStretchStopPct: data.darkStretch.totalPct,
    retention: { enrolled: data.retention.enrolled, week12: data.retention.active[last], pct: data.retention.week12Pct },
  };
}
