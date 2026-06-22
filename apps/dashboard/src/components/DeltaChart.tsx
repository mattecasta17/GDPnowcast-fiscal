"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { COLORS, COVID, data, fmt, periodLabel, periodTick } from "@/lib/data";
import { ChartFrame } from "./ChartFrame";

export function DeltaChart() {
  const [hideCovid, setHideCovid] = useState(true);
  const rows = data.comparison.per_quarter.filter((r) => !(hideCovid && COVID.has(r.period)));

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink">Where the fiscal block helps, quarter by quarter</h3>
          <p className="text-xs text-muted">
            |error| Fiscal-enhanced minus |error| Staff Nowcast (pp). Below zero = the fiscal block
            is more accurate that quarter.
          </p>
        </div>
        <button
          onClick={() => setHideCovid((v) => !v)}
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:text-ink"
        >
          {hideCovid ? "Show 2020 (COVID)" : "Hide 2020 (COVID)"}
        </button>
      </div>
      <ChartFrame height={300}>
        {(w) => (
        <BarChart width={w} height={300} data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
          <XAxis
            dataKey="period"
            tickFormatter={periodTick}
            tick={{ fontSize: 11, fill: "#64748b" }}
            interval="preserveStartEnd"
            minTickGap={14}
          />
          <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={44} />
          <Tooltip
            formatter={(v: number) => [`${fmt(v)} pp`, "|err| Fiscal-enhanced - |err| Staff"]}
            labelFormatter={(p: string) => periodLabel(p)}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
            cursor={{ fill: "#f8fafc" }}
          />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Bar dataKey="abs_error_delta" radius={[2, 2, 2, 2]}>
            {rows.map((r) => (
              <Cell key={r.period} fill={r.abs_error_delta <= 0 ? COLORS.good : COLORS.bad} />
            ))}
          </Bar>
        </BarChart>
        )}
      </ChartFrame>
      <div className="mt-3 flex gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: COLORS.good }} />
          Fiscal-enhanced better
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: COLORS.bad }} />
          Staff Nowcast better
        </span>
      </div>
    </div>
  );
}
