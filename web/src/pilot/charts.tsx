// Not in Figr: built plainly from design tokens. Dependency-free inline SVG chart primitives
// for the simulated pilot page. Khalasi = teal, control = neutral grey (validated pair);
// every multi-series chart also carries a legend and direct labels so identity is never colour-alone.
import type { ReactNode } from "react";
import type { Arm } from "./generate";

export const ARM_COLOR: Record<Arm, string> = {
  khalasi: "var(--color-teal)",
  control: "var(--color-ink-faint)",
};
export const ARM_LABEL: Record<Arm, string> = { khalasi: "Khalasi", control: "Control" };

export type Series = { name: string; color: string; values: number[]; dashed?: boolean };

const W = 640;
const H = 210;
const PL = 44;
const PR = 56;
const PT = 16;
const PB = 26;
const IW = W - PL - PR;
const IH = H - PT - PB;

const GRID = "var(--color-line)";
const AXIS_TEXT = "var(--color-ink-faint)";
const LABEL_TEXT = "var(--color-ink-muted)";
const FONT = "var(--font-mono)";

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  const n = v / p;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  return step * p;
}

const fmtDefault = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

/* ---------- Frame, chip, legend ---------- */

export function SimChip({ small }: { small?: boolean }) {
  return (
    <span
      className={`shrink-0 rounded-md border border-warn/50 bg-warn-deep font-medium text-warn ${
        small ? "px-2 py-0.5 text-sm" : "px-2.5 py-1 text-base"
      }`}
    >
      Simulated
    </span>
  );
}

export function Legend({ series }: { series: Series[] }) {
  return (
    <ul className="flex items-center gap-4 text-base text-ink-muted" aria-label="Legend">
      {series.map((s) => (
        <li key={s.name} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{
              background: s.color,
              boxShadow: s.dashed ? "inset 0 0 0 1px var(--color-line-strong)" : undefined,
            }}
          />
          {s.name}
        </li>
      ))}
    </ul>
  );
}

export function ChartPanel({
  title,
  caption,
  legend,
  children,
  className = "",
}: {
  title: string;
  caption: ReactNode;
  legend?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section aria-label={title} className={`flex flex-col rounded-panel border border-line bg-panel ${className}`}>
      <div className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-line px-5">
        <h2 className="truncate text-lg font-semibold">{title}</h2>
        <div className="flex items-center gap-4">
          {legend}
          <SimChip small />
        </div>
      </div>
      <div className="px-5 pt-4">{children}</div>
      <p className="px-5 pb-4 pt-3 text-base leading-snug text-ink-muted">{caption}</p>
    </section>
  );
}

/* ---------- Shared axis bits ---------- */

function Grid({ max, min = 0, format = fmtDefault, unit = "" }: { max: number; min?: number; format?: (v: number) => string; unit?: string }) {
  const ticks = [min, min + (max - min) / 2, max];
  return (
    <g aria-hidden>
      {ticks.map((t) => {
        const y = PT + IH - ((t - min) / (max - min)) * IH;
        return (
          <g key={t}>
            <line x1={PL} x2={W - PR} y1={y} y2={y} stroke={GRID} strokeWidth={1} />
            <text x={PL - 6} y={y + 4} textAnchor="end" fontSize={11} fontFamily={FONT} fill={AXIS_TEXT}>
              {format(t)}
              {unit}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function XLabels({ labels }: { labels: string[] }) {
  const step = IW / labels.length;
  return (
    <g aria-hidden>
      {labels.map((l, i) => (
        <text
          key={l}
          x={PL + step * i + step / 2}
          y={H - 8}
          textAnchor="middle"
          fontSize={11}
          fontFamily={FONT}
          fill={AXIS_TEXT}
        >
          {l}
        </text>
      ))}
    </g>
  );
}

/** Bar with 4px rounded top corners, anchored to the baseline. */
function topRounded(x: number, y: number, w: number, h: number, r = 4): string {
  const rr = Math.min(r, w / 2, h);
  if (h <= 0) return "";
  return `M${x},${y + h} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + w - rr} Q${x + w},${y} ${x + w},${y + rr} V${y + h} Z`;
}

/* ---------- Grouped bars (1 to 2 series per category) ---------- */

export function GroupedBars({
  labels,
  series,
  ariaLabel,
  yMax,
  unit = "",
  format = fmtDefault,
  labelLast = true,
}: {
  labels: string[];
  series: Series[];
  ariaLabel: string;
  yMax?: number;
  unit?: string;
  format?: (v: number) => string;
  labelLast?: boolean;
}) {
  const max = yMax ?? niceMax(Math.max(...series.flatMap((s) => s.values)) * 1.15);
  const groupW = IW / labels.length;
  const pad = Math.max(3, groupW * 0.18);
  const gap = 2;
  const barW = (groupW - 2 * pad - gap * (series.length - 1)) / series.length;
  const y = (v: number) => PT + IH - (v / max) * IH;
  const base = PT + IH;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={ariaLabel} className="block">
      <Grid max={max} unit={unit} format={format} />
      {labels.map((label, i) =>
        series.map((s, j) => {
          const v = s.values[i] ?? 0;
          const x = PL + groupW * i + pad + j * (barW + gap);
          const top = y(v);
          const isLabel = labelLast && (i === labels.length - 1 || i === 0);
          return (
            <g key={`${label}-${s.name}`}>
              <path d={topRounded(x, top, barW, base - top)} fill={s.color}>
                <title>{`${label} · ${s.name}: ${format(v)}${unit}`}</title>
              </path>
              {isLabel && (
                <text
                  x={x + barW / 2}
                  y={top - 4}
                  textAnchor="middle"
                  fontSize={11}
                  fontFamily={FONT}
                  fill={LABEL_TEXT}
                >
                  {format(v)}
                </text>
              )}
            </g>
          );
        }),
      )}
      <line x1={PL} x2={W - PR} y1={base} y2={base} stroke="var(--color-line-strong)" strokeWidth={1} aria-hidden />
      <XLabels labels={labels} />
    </svg>
  );
}

/* ---------- Lines (1 to 2 series), optional reference line ---------- */

export function Lines({
  labels,
  series,
  ariaLabel,
  yMin,
  yMax,
  unit = "",
  format = fmtDefault,
  labelFormat,
  refLine,
  area,
}: {
  labels: string[];
  series: Series[];
  ariaLabel: string;
  yMin?: number;
  yMax?: number;
  unit?: string;
  /** Axis tick format. */
  format?: (v: number) => string;
  /** Format for direct labels and tooltips; defaults to the axis format. */
  labelFormat?: (v: number) => string;
  refLine?: { value: number; label: string };
  area?: boolean;
}) {
  const fmtLabel = labelFormat ?? format;
  const all = series.flatMap((s) => s.values);
  const dataMax = Math.max(...all, refLine?.value ?? 0);
  const dataMin = Math.min(...all, refLine?.value ?? Infinity);
  const max = yMax ?? niceMax(dataMax * 1.1);
  const min = yMin ?? (dataMin > dataMax * 0.5 ? Math.floor(dataMin * 0.8) : 0);
  const step = IW / labels.length;
  const x = (i: number) => PL + step * i + step / 2;
  const y = (v: number) => PT + IH - ((v - min) / (max - min)) * IH;
  const base = PT + IH;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={ariaLabel} className="block">
      <Grid max={max} min={min} unit={unit} format={format} />
      {refLine && (
        <g aria-hidden>
          <line
            x1={PL}
            x2={W - PR}
            y1={y(refLine.value)}
            y2={y(refLine.value)}
            stroke="var(--color-marigold)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
          <text x={PL + 6} y={y(refLine.value) - 6} textAnchor="start" fontSize={11} fontFamily={FONT} fill={LABEL_TEXT}>
            {refLine.label}
          </text>
        </g>
      )}
      {series.map((s) => {
        const pts = s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
        const last = s.values.length - 1;
        return (
          <g key={s.name}>
            {area && (
              <polygon
                points={`${x(0)},${base} ${pts} ${x(last)},${base}`}
                fill={s.color}
                opacity={0.12}
                aria-hidden
              />
            )}
            <polyline
              points={pts}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeDasharray={s.dashed ? "6 4" : undefined}
            />
            {s.values.map((v, i) => (
              <circle key={i} cx={x(i)} cy={y(v)} r={4} fill={s.color} stroke="var(--color-panel)" strokeWidth={2}>
                <title>{`${labels[i]} · ${s.name}: ${fmtLabel(v)}${unit}`}</title>
              </circle>
            ))}
            <text
              x={x(last) + 9}
              y={y(s.values[last]) + 4}
              fontSize={11}
              fontFamily={FONT}
              fill={LABEL_TEXT}
              aria-hidden
            >
              {fmtLabel(s.values[last])}
            </text>
          </g>
        );
      })}
      <line x1={PL} x2={W - PR} y1={base} y2={base} stroke="var(--color-line-strong)" strokeWidth={1} aria-hidden />
      <XLabels labels={labels} />
    </svg>
  );
}

/* ---------- Part-of-whole bars: kept (filled) within promised (outlined) ---------- */

export function PartBars({
  labels,
  part,
  whole,
  partName,
  wholeName,
  color,
  ariaLabel,
}: {
  labels: string[];
  part: number[];
  whole: number[];
  partName: string;
  wholeName: string;
  color: string;
  ariaLabel: string;
}) {
  const max = niceMax(Math.max(...whole) * 1.15);
  const groupW = IW / labels.length;
  const pad = Math.max(3, groupW * 0.22);
  const barW = groupW - 2 * pad;
  const y = (v: number) => PT + IH - (v / max) * IH;
  const base = PT + IH;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={ariaLabel} className="block">
      <Grid max={max} />
      {labels.map((label, i) => {
        const xx = PL + groupW * i + pad;
        const wTop = y(whole[i]);
        const pTop = y(part[i]);
        const pctKept = whole[i] > 0 ? Math.round((100 * part[i]) / whole[i]) : 0;
        return (
          <g key={label}>
            <path d={topRounded(xx, wTop, barW, base - wTop)} fill="var(--color-raised)" stroke="var(--color-line-strong)" strokeWidth={1}>
              <title>{`${label} · ${wholeName}: ${whole[i]}`}</title>
            </path>
            <path d={topRounded(xx, pTop, barW, base - pTop)} fill={color}>
              <title>{`${label} · ${partName}: ${part[i]} of ${whole[i]} (${pctKept}%)`}</title>
            </path>
            <text x={xx + barW / 2} y={wTop - 4} textAnchor="middle" fontSize={11} fontFamily={FONT} fill={LABEL_TEXT} aria-hidden>
              {pctKept}%
            </text>
          </g>
        );
      })}
      <line x1={PL} x2={W - PR} y1={base} y2={base} stroke="var(--color-line-strong)" strokeWidth={1} aria-hidden />
      <XLabels labels={labels} />
    </svg>
  );
}
