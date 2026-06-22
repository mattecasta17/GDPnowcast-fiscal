"use client";

import { useMemo, useState } from "react";
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
import { COLORS, data, fmt, periodLabel } from "@/lib/data";
import type { Variant } from "@/lib/types";
import { ChartFrame } from "./ChartFrame";

type Mode = Variant | "both";

const MODE_LABEL: Record<Mode, string> = { baseline: "Staff", fiscal: "Fiscal", both: "Both" };

export function WeeklyExplorer() {
  const { periods } = data.meta;
  const [period, setPeriod] = useState("2017q1");
  const [mode, setMode] = useState<Mode>("both");

  const head = useMemo(() => {
    const b = data.headline.baseline.find((r) => r.period === period)!;
    const f = data.headline.fiscal.find((r) => r.period === period)!;
    return { b, f, target: b.gdp_advance };
  }, [period]);

  const rows = useMemo(() => {
    const bw = data.weekly.baseline[period] ?? [];
    const fw = data.weekly.fiscal[period] ?? [];
    const map = new Map<string, { vintage: string; baseline?: number; fiscal?: number }>();
    for (const r of bw) map.set(r.vintage, { ...(map.get(r.vintage) ?? { vintage: r.vintage }), baseline: r.y_new });
    for (const r of fw) map.set(r.vintage, { ...(map.get(r.vintage) ?? { vintage: r.vintage }), fiscal: r.y_new });
    return [...map.values()].sort((a, b) => a.vintage.localeCompare(b.vintage));
  }, [period]);

  const skippedB = data.skipped.baseline[period] ?? [];

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink">Within-quarter nowcast path</h3>
          <p className="text-xs text-muted">
            How the nowcast evolves week by week as data arrives, vs the realized BEA advance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="rounded-lg border border-line bg-white px-3 py-1.5 text-sm font-medium text-ink shadow-sm focus:border-slate-300 focus:outline-none"
          >
            {periods.map((p) => (
              <option key={p} value={p}>
                {periodLabel(p)}
              </option>
            ))}
          </select>
          <div className="inline-flex overflow-hidden rounded-lg border border-line text-xs font-medium">
            {(["baseline", "fiscal", "both"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1.5 transition-colors ${
                  mode === m ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:text-ink"
                }`}
              >
                {MODE_LABEL[m]}
              </button>
            ))}
          </div>
        </div>
      </div>

      <ChartFrame height={360}>
        {(w) => (
        <LineChart width={w} height={360} data={rows} margin={{ top: 8, right: 14, left: -8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis
            dataKey="vintage"
            tickFormatter={(v: string) => v.slice(5)}
            tick={{ fontSize: 11, fill: "#64748b" }}
            minTickGap={18}
          />
          <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={44} />
          <Tooltip
            formatter={(value: number, name: string) => [`${fmt(value)} pp`, name]}
            labelFormatter={(v: string) => `vintage ${v}`}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine
            y={head.target}
            stroke={COLORS.advance}
            strokeDasharray="6 4"
            label={{ value: `advance ${fmt(head.target)}`, position: "insideTopRight", fontSize: 11, fill: "#0f172a" }}
          />
          {(mode === "baseline" || mode === "both") && (
            <Line
              type="monotone"
              dataKey="baseline"
              name="Staff Nowcast"
              stroke={COLORS.baseline}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls
            />
          )}
          {(mode === "fiscal" || mode === "both") && (
            <Line
              type="monotone"
              dataKey="fiscal"
              name="Fiscal-enhanced DFM"
              stroke={COLORS.fiscal}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls
            />
          )}
        </LineChart>
        )}
      </ChartFrame>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs text-slate-600 sm:grid-cols-4">
        <Fact label="BEA advance" value={`${fmt(head.target)} pp`} />
        <Fact label="Staff Nowcast" value={`${fmt(head.b.headline_nowcast)} pp`} />
        <Fact label="Fiscal-enhanced" value={`${fmt(head.f.headline_nowcast)} pp`} />
        <Fact label="Weekly vintages" value={`${rows.length}`} />
      </div>
      {skippedB.length > 0 ? (
        <p className="mt-3 text-xs text-slate-500">
          Skipped vintages (no-news / release-week crash cases, faithfully reproduced from v1):{" "}
          <span className="font-mono">{skippedB.join(", ")}</span>
        </p>
      ) : null}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted">{label}: </span>
      <span className="font-mono font-medium text-ink">{value}</span>
    </div>
  );
}
