"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { COLORS, COVID, data, fmt, periodLabel, periodTick } from "@/lib/data";
import { ChartFrame } from "./ChartFrame";

export function HeadlineChart() {
  const [hideCovid, setHideCovid] = useState(true);

  const baseByPeriod = new Map(data.headline.baseline.map((r) => [r.period, r]));
  const fiscalByPeriod = new Map(data.headline.fiscal.map((r) => [r.period, r]));

  const rows = data.meta.periods
    .filter((p) => !(hideCovid && COVID.has(p)))
    .map((p) => ({
      period: p,
      advance: baseByPeriod.get(p)!.gdp_advance,
      baseline: baseByPeriod.get(p)!.headline_nowcast,
      fiscal: fiscalByPeriod.get(p)!.headline_nowcast,
    }));

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink">Nowcast vs BEA advance</h3>
          <p className="text-xs text-muted">
            Annualized real-GDP growth (pp), at the (advance - 1 day) cutoff
          </p>
        </div>
        <button
          onClick={() => setHideCovid((v) => !v)}
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:text-ink"
        >
          {hideCovid ? "Show 2020 (COVID)" : "Hide 2020 (COVID)"}
        </button>
      </div>
      {hideCovid ? (
        <p className="mb-3 text-xs text-amber-700">
          2020 is hidden so the normal-times range is readable. In 2020q2 the advance fell to about
          -32 pp annualized; including it compresses every other quarter.
        </p>
      ) : null}
      <ChartFrame height={380}>
        {(w) => (
        <LineChart width={w} height={380} data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis
            dataKey="period"
            tickFormatter={periodTick}
            tick={{ fontSize: 11, fill: "#64748b" }}
            interval="preserveStartEnd"
            minTickGap={16}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickFormatter={(v) => `${v}`}
            width={44}
            label={{ value: "pp", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
          />
          <Tooltip
            formatter={(value: number, name: string) => [`${fmt(value)} pp`, name]}
            labelFormatter={(p: string) => periodLabel(p)}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine y={0} stroke="#cbd5e1" />
          <Line
            type="monotone"
            dataKey="advance"
            name="BEA advance (target)"
            stroke={COLORS.advance}
            strokeWidth={2.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="baseline"
            name="Staff Nowcast"
            stroke={COLORS.baseline}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="fiscal"
            name="Fiscal-enhanced DFM"
            stroke={COLORS.fiscal}
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
          />
        </LineChart>
        )}
      </ChartFrame>
    </div>
  );
}
