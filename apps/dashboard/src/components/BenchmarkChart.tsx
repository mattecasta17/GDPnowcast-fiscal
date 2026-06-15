"use client";

import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { COLORS, data, fmt } from "@/lib/data";

const ORDER = ["dfm", "mean", "rw", "ar1", "arma11"] as const;
const SHORT: Record<string, string> = { dfm: "DFM", mean: "Mean", rw: "RW", ar1: "AR(1)", arma11: "ARMA" };

function Panel({ sample, title }: { sample: "ex_2020" | "all"; title: string }) {
  const rows = ORDER.map((m) => ({
    model: SHORT[m],
    rmse: data.benchmarks.metrics[m][sample].rmse,
    isDfm: m === "dfm",
  }));
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-slate-600">{title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows} margin={{ top: 18, right: 8, left: -10, bottom: 0 }}>
          <XAxis dataKey="model" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={40} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(v: number) => [`${fmt(v)} pp`, "RMSE"]}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
            cursor={{ fill: "#f8fafc" }}
          />
          <Bar dataKey="rmse" radius={[3, 3, 0, 0]}>
            <LabelList dataKey="rmse" position="top" formatter={(v: number) => fmt(v, 1)} fontSize={10} fill="#475569" />
            {rows.map((r) => (
              <Cell key={r.model} fill={r.isDfm ? COLORS.baseline : "#cbd5e1"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BenchmarkChart() {
  return (
    <div className="card">
      <h3 className="text-base font-semibold text-ink">RMSE by model</h3>
      <p className="mb-4 text-xs text-muted">
        DFM (blue) is mid-pack in calm times but does not blow up over the full sample. Note the
        very different vertical scales.
      </p>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Panel sample="ex_2020" title="Normal times (ex-2020), 30 quarters" />
        <Panel sample="all" title="All 34 quarters (incl. 2020)" />
      </div>
    </div>
  );
}
