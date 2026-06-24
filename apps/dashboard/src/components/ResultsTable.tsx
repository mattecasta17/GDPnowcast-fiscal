"use client";

import { useState } from "react";
import { data, fmt, fmtSigned } from "@/lib/data";
import type { BenchPerQuarter } from "@/lib/types";

type Metric = "rmse" | "mae" | "bias";

const METRICS: { key: Metric; label: string }[] = [
  { key: "rmse", label: "RMSE" },
  { key: "mae", label: "MAE" },
  { key: "bias", label: "Bias" },
];

const MODELS: { key: string; label: string; dfm?: boolean }[] = [
  { key: "staff", label: "Staff Nowcast", dfm: true },
  { key: "fiscal", label: "Fiscal-enhanced", dfm: true },
  { key: "mean", label: "Historical mean" },
  { key: "rw", label: "Random walk" },
  { key: "ar1", label: "AR(1)" },
  { key: "arma11", label: "ARMA(1,1)" },
];

const COVID = new Set(data.meta.covid_periods);
const PERIODS: { key: string; label: string; sub: string; test: (p: string) => boolean }[] = [
  { key: "exc", label: "Full Sample ex Covid", sub: "30 q", test: (p) => !COVID.has(p) },
  { key: "pre", label: "Pre-COVID", sub: "2017-2019", test: (p) => Number(p.slice(0, 4)) <= 2019 },
  { key: "post", label: "Post-COVID", sub: "2021-2025", test: (p) => Number(p.slice(0, 4)) >= 2021 },
];

const benchRows: BenchPerQuarter[] = data.benchmarks.per_quarter;
const ERR: Record<string, Map<string, number>> = {
  staff: new Map(data.headline.baseline.map((r) => [r.period, r.error])),
  fiscal: new Map(data.headline.fiscal.map((r) => [r.period, r.error])),
  mean: new Map(benchRows.map((r) => [r.period, r.mean_error])),
  rw: new Map(benchRows.map((r) => [r.period, r.rw_error])),
  ar1: new Map(benchRows.map((r) => [r.period, r.ar1_error])),
  arma11: new Map(benchRows.map((r) => [r.period, r.arma11_error])),
};
const ALL_PERIODS = data.meta.periods;

function aggregate(errs: number[], metric: Metric): number {
  const n = errs.length;
  // Bias in the nowcast - realized convention (thesis eq. 17): negate the realized - nowcast error.
  if (metric === "bias") return -errs.reduce((s, e) => s + e, 0) / n;
  if (metric === "mae") return errs.reduce((s, e) => s + Math.abs(e), 0) / n;
  return Math.sqrt(errs.reduce((s, e) => s + e * e, 0) / n);
}

export function ResultsTable() {
  const [metric, setMetric] = useState<Metric>("rmse");

  const values: Record<string, Record<string, number>> = {};
  for (const per of PERIODS) {
    const ps = ALL_PERIODS.filter(per.test);
    values[per.key] = {};
    for (const m of MODELS) {
      const errs = ps.map((p) => ERR[m.key].get(p) as number);
      values[per.key][m.key] = aggregate(errs, metric);
    }
  }

  // Best (most accurate) value per column: lowest RMSE/MAE, smallest |bias|.
  const best: Record<string, number> = {};
  for (const per of PERIODS) {
    const vals = MODELS.map((m) => values[per.key][m.key]);
    best[per.key] = metric === "bias" ? Math.min(...vals.map((v) => Math.abs(v))) : Math.min(...vals);
  }
  const isBest = (perKey: string, v: number) =>
    metric === "bias"
      ? Math.abs(Math.abs(v) - best[perKey]) < 1e-9
      : Math.abs(v - best[perKey]) < 1e-9;

  const fmtVal = (v: number) => (metric === "bias" ? fmtSigned(v) : fmt(v));

  return (
    <div className="card overflow-x-auto">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-xs text-muted">
          Pre-advance forecast error by sample (pp). Lower RMSE and MAE are better; a bias closer to
          zero is better (bias = nowcast − realized). The most accurate value in each column is shown
          in bold.
        </p>
        <div className="inline-flex overflow-hidden rounded-lg border border-line text-xs font-medium">
          {METRICS.map((mt) => (
            <button
              key={mt.key}
              onClick={() => setMetric(mt.key)}
              className={`px-3 py-1.5 transition-colors ${
                metric === mt.key
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-600 hover:text-ink"
              }`}
            >
              {mt.label}
            </button>
          ))}
        </div>
      </div>

      <table className="w-full min-w-[600px] text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            <th className="py-2 pr-3 font-medium">Model</th>
            {PERIODS.map((p) => (
              <th key={p.key} className="px-3 py-2 text-right font-medium">
                <div>{p.label}</div>
                <div className="font-normal normal-case text-slate-400">{p.sub}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {MODELS.map((m, i) => (
            <tr
              key={m.key}
              className={`border-b border-line/70 ${i === 2 ? "border-t-2 border-t-line" : ""} ${
                m.dfm ? "bg-slate-50" : ""
              }`}
            >
              <td
                className={`py-2 pr-3 font-sans ${
                  m.key === "fiscal"
                    ? "font-semibold text-fiscal"
                    : m.key === "staff"
                      ? "font-semibold text-baseline"
                      : "text-slate-700"
                }`}
              >
                {m.label}
              </td>
              {PERIODS.map((p) => {
                const v = values[p.key][m.key];
                return (
                  <td
                    key={p.key}
                    className={`px-3 py-2 text-right font-mono ${
                      isBest(p.key, v) ? "font-semibold text-ink" : "text-slate-700"
                    }`}
                  >
                    {fmtVal(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
