"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { COLORS, data, fmt, fmtSigned } from "@/lib/data";
import { ChartFrame } from "./ChartFrame";

const NEWS = "#f59e0b";

type Row = { label: string; macro: number; fiscal: number; gain: number; news: number };

const QS: [string, string][] = [
  ["q1", "Q1"],
  ["q2", "Q2"],
  ["q3", "Q3"],
  ["q4", "Q4"],
];

const rows: Row[] = QS.map(([k, label]) => {
  const qs = data.fiscal_impact.per_quarter.filter((r) => r.period.slice(4) === k);
  const n = qs.length;
  const macro = qs.reduce((s, r) => s + r.err_staff, 0) / n;
  const fiscal = qs.reduce((s, r) => s + (r.err_staff - r.gain), 0) / n;
  const news = qs.reduce((s, r) => s + Math.abs(r.impact), 0) / n;
  return { label, macro, fiscal, gain: macro - fiscal, news };
});

const q2 = rows.find((r) => r.label === "Q2") ?? rows[1];
const corrPost = data.fiscal_impact.summary.corr_post;

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Row }[] }) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-semibold text-ink">{r.label} (non-COVID)</p>
      <p className="mt-0.5 text-slate-600">
        MAE macro <span className="font-mono text-ink">{fmt(r.macro, 3)}</span>
      </p>
      <p className="text-slate-600">
        MAE fiscal <span className="font-mono text-fiscal">{fmt(r.fiscal, 3)}</span>
      </p>
      <p className="text-slate-600">
        gain <span className="font-mono text-ink">{fmtSigned(r.gain, 3)}</span>
      </p>
      <p className="text-slate-600">
        |fiscal news| <span className="font-mono" style={{ color: NEWS }}>{fmt(r.news, 3)}</span>
      </p>
    </div>
  );
}

export function Q2GainChart() {
  return (
    <div className="card">
      <h3 className="text-base font-semibold text-ink">The gain concentrates in the second quarter</h3>
      <p className="mb-4 text-xs text-muted">
        Mean absolute error by calendar quarter, macro-only versus fiscal (non-COVID quarters). The
        line is the average size of the fiscal block&apos;s news. Where the news peaks, so does the
        gain.
      </p>
      <ChartFrame height={300}>
        {(w) => (
          <ComposedChart
            width={w}
            height={300}
            data={rows}
            margin={{ top: 8, right: 12, left: 0, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} />
            <YAxis
              yAxisId="mae"
              tick={{ fontSize: 11, fill: "#64748b" }}
              width={44}
              label={{ value: "MAE (pp)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
            />
            <YAxis
              yAxisId="news"
              orientation="right"
              tick={{ fontSize: 11, fill: "#64748b" }}
              width={40}
              label={{ value: "|news| (pp)", angle: 90, position: "insideRight", fontSize: 11, fill: "#94a3b8" }}
            />
            <Tooltip content={<Tip />} cursor={{ fill: "#f8fafc" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar yAxisId="mae" dataKey="macro" name="Macro-only" fill={COLORS.baseline} radius={[3, 3, 0, 0]} />
            <Bar yAxisId="mae" dataKey="fiscal" name="Fiscal-enhanced" fill={COLORS.fiscal} radius={[3, 3, 0, 0]} />
            <Line
              yAxisId="news"
              type="monotone"
              dataKey="news"
              name="|fiscal news|"
              stroke={NEWS}
              strokeWidth={2}
              dot={{ r: 3, fill: NEWS }}
            />
          </ComposedChart>
        )}
      </ChartFrame>
      <p className="mt-3 text-xs text-slate-500">
        The fiscal block lowers the MAE most in the second quarter ({fmt(q2.macro, 3)} &rarr;{" "}
        {fmt(q2.fiscal, 3)}, a {fmtSigned(q2.gain, 3)} pp gain), exactly where the deficit&apos;s news
        peaks: the April tax season drives the largest swings in federal cash flows. The same link
        holds quarter by quarter &mdash; the size of the fiscal news and the accuracy gain move together
        (correlation {fmtSigned(corrPost, 2)} after 2020).
      </p>
    </div>
  );
}
