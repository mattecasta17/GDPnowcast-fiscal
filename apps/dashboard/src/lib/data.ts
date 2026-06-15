import raw from "@/data/dashboard.json";
import type { Dashboard } from "./types";

// The JSON is generated/validated by tools/build_dashboard_data.py and pinned by a Python test;
// we trust its shape here rather than carrying TS's inferred giant literal type.
export const data = raw as unknown as Dashboard;

export const COVID = new Set(data.meta.covid_periods);

/** "2017q1" -> "2017 Q1" */
export function periodLabel(p: string): string {
  const [y, q] = p.split("q");
  return `${y} Q${q}`;
}

/** "2017q1" -> "'17 Q1" (compact axis tick) */
export function periodTick(p: string): string {
  const [y, q] = p.split("q");
  return `'${y.slice(2)} Q${q}`;
}

export function fmt(x: number | null | undefined, d = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "-";
  return x.toFixed(d);
}

export function fmtSigned(x: number, d = 2): string {
  return (x >= 0 ? "+" : "") + x.toFixed(d);
}

export function fmtPct(x: number, d = 1): string {
  return (x * 100).toFixed(d) + "%";
}

export const COLORS = {
  baseline: "#2563eb",
  fiscal: "#db2777",
  advance: "#0f172a",
  covid: "#f59e0b",
  mean: "#0891b2",
  rw: "#9333ea",
  ar1: "#16a34a",
  arma11: "#ca8a04",
  good: "#16a34a",
  bad: "#dc2626",
} as const;

export const MODEL_LABELS: Record<string, string> = {
  dfm: "DFM (this model)",
  mean: "Historical mean",
  rw: "Random walk",
  ar1: "AR(1)",
  arma11: "ARMA(1,1)",
};
