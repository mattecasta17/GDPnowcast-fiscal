"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { COLORS, COVID, data, fmt, periodLabel, periodTick } from "@/lib/data";
import { ChartFrame } from "./ChartFrame";

export function QuarterErrorChart() {
  const [hideCovid, setHideCovid] = useState(true);

  const fiscalByPeriod = new Map(data.headline.fiscal.map((r) => [r.period, r]));
  const rows = data.headline.baseline
    .filter((r) => !(hideCovid && COVID.has(r.period)))
    .map((r) => ({
      period: r.period,
      baseline: r.error,
      fiscal: fiscalByPeriod.get(r.period)!.error,
      covid: COVID.has(r.period),
    }));

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink">Per-quarter forecast error</h3>
          <p className="text-xs text-muted">nowcast minus advance (pp); 0 is a perfect call</p>
        </div>
        <button
          onClick={() => setHideCovid((v) => !v)}
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:text-ink"
        >
          {hideCovid ? "Show 2020 (COVID)" : "Hide 2020 (COVID)"}
        </button>
      </div>
      <ChartFrame height={340}>
        {(w) => (
        <BarChart width={w} height={340} data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 4 }} barCategoryGap="18%">
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
            formatter={(value: number, name: string) => [`${fmt(value)} pp`, name]}
            labelFormatter={(p: string) => periodLabel(p)}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
            cursor={{ fill: "#f8fafc" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Bar dataKey="baseline" name="DFM baseline" fill={COLORS.baseline} radius={[2, 2, 0, 0]}>
            {rows.map((r) => (
              <Cell key={r.period} fillOpacity={r.covid ? 0.45 : 1} />
            ))}
          </Bar>
          <Bar dataKey="fiscal" name="DFM fiscal" fill={COLORS.fiscal} radius={[2, 2, 0, 0]}>
            {rows.map((r) => (
              <Cell key={r.period} fillOpacity={r.covid ? 0.45 : 1} />
            ))}
          </Bar>
        </BarChart>
        )}
      </ChartFrame>
    </div>
  );
}
