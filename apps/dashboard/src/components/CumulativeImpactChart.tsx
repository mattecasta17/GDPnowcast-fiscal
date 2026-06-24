"use client";

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
import { COLORS, data, fmt, periodLabel, periodTick } from "@/lib/data";
import { ChartFrame } from "./ChartFrame";

const PRE = "#94a3b8";

type Row = { period: string; impact: number; post: boolean };

const rows: Row[] = data.fiscal_impact.per_quarter.map((r) => ({
  period: r.period,
  impact: r.impact,
  post: Number(r.period.slice(0, 4)) >= 2021,
}));

const s = data.fiscal_impact.summary;

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Row }[] }) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-semibold text-ink">{periodLabel(r.period)}</p>
      <p className="mt-0.5 text-slate-600">
        fiscal impact <span className="font-mono text-ink">{fmt(r.impact, 2)} pp</span>
      </p>
    </div>
  );
}

export function CumulativeImpactChart() {
  return (
    <div className="card">
      <h3 className="text-base font-semibold text-ink">
        The fiscal block&apos;s contribution exploded after 2020
      </h3>
      <p className="mb-4 text-xs text-muted">
        Total revision the fiscal block imparts to each quarter&apos;s GDP nowcast (absolute, pp). The
        2020 quarters are excluded; the gap on the axis marks the pandemic.
      </p>
      <ChartFrame height={300}>
        {(w) => (
          <BarChart width={w} height={300} data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
            <XAxis
              dataKey="period"
              tickFormatter={periodTick}
              tick={{ fontSize: 10, fill: "#64748b" }}
              interval={2}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#64748b" }}
              width={40}
              label={{ value: "impact (pp)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
            />
            <ReferenceLine
              y={s.mean_impact_pre}
              stroke="#cbd5e1"
              strokeDasharray="4 4"
              label={{ value: `pre-2020 avg ${fmt(s.mean_impact_pre, 2)}`, position: "insideTopLeft", fontSize: 10, fill: "#94a3b8" }}
            />
            <Tooltip content={<Tip />} cursor={{ fill: "#f8fafc" }} />
            <Bar dataKey="impact" radius={[2, 2, 0, 0]}>
              {rows.map((r) => (
                <Cell key={r.period} fill={r.post ? COLORS.fiscal : PRE} />
              ))}
            </Bar>
          </BarChart>
        )}
      </ChartFrame>
      <div className="mt-3 flex items-center gap-4 text-[11px] text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: PRE }} /> pre-2020
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: COLORS.fiscal }} />{" "}
          post-2020
        </span>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Before 2020 the federal deficit followed a path the model could anticipate, so its releases
        carried almost no news (average {fmt(s.mean_impact_pre, 2)} pp). After 2020 the deficit became
        large and persistently expansionary, and its surprises move the nowcast by{" "}
        {fmt(s.mean_impact_post, 2)} pp on average &mdash; roughly {fmt(s.impact_ratio_post_pre, 1)}{" "}
        times more. The fiscal block matters most exactly when fiscal policy is most active.
      </p>
    </div>
  );
}
