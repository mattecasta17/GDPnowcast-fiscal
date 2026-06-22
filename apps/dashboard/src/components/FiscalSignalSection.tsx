"use client";

import {
  CartesianGrid,
  Legend,
  ReferenceLine,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { COLORS, data, fmt, fmtSigned, periodLabel } from "@/lib/data";
import { ChartFrame } from "./ChartFrame";
import { Stat } from "./ui";

const POST = COLORS.fiscal;
const PRE = "#94a3b8";

type Pt = { period: string; impact: number; gain: number };

function ScatterTip({ active, payload }: { active?: boolean; payload?: { payload: Pt }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-semibold text-ink">{periodLabel(p.period)}</p>
      <p className="mt-0.5 text-slate-600">
        fiscal impact <span className="font-mono text-ink">{fmt(p.impact, 2)}</span>
      </p>
      <p className="text-slate-600">
        accuracy gain <span className="font-mono text-ink">{fmtSigned(p.gain, 2)} pp</span>
      </p>
    </div>
  );
}

export function FiscalSignalSection() {
  const fi = data.fiscal_impact;
  const s = fi.summary;
  const rows = fi.per_quarter.map((r) => ({ period: r.period, impact: r.impact, gain: r.gain }));
  const pre = rows.filter((r) => Number(r.period.slice(0, 4)) <= 2019);
  const post = rows.filter((r) => Number(r.period.slice(0, 4)) >= 2021);
  const byVar = fi.fiscal_block.map((v) => ({ ...v, corr: s.corr_by_variable[v.id] ?? 0 }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat
          label="Fiscal news, post vs pre-COVID"
          value={`${fmt(s.impact_ratio_post_pre, 1)}×`}
          accent="fiscal"
          sub={`bigger surprises after 2020 (${fmt(s.mean_impact_pre, 2)} → ${fmt(s.mean_impact_post, 2)})`}
        />
        <Stat
          label="Impact ↔ accuracy gain"
          value={fmtSigned(s.corr_post, 2)}
          accent="fiscal"
          sub={`post-COVID correlation (${fmtSigned(s.corr_all, 2)} over all non-COVID)`}
        />
        <Stat
          label="Controlling for error size"
          value={fmtSigned(s.corr_partial_post, 2)}
          accent="fiscal"
          sub="partial corr, post-COVID - not just a volatility artifact"
        />
      </div>

      <div className="card">
        <h3 className="text-base font-semibold text-ink">
          Bigger fiscal surprises, bigger accuracy gain
        </h3>
        <p className="mb-4 text-xs text-muted">
          Each dot is a non-COVID quarter. X = the fiscal block&apos;s news that quarter (|actual -
          forecast| &times; weight, summed over weekly vintages). Y = how much more accurate the
          Fiscal-enhanced DFM was than the Staff Nowcast. Up-and-to-the-right = the fiscal signal paid
          off.
        </p>
        <ChartFrame height={340}>
          {(w) => (
            <ScatterChart width={w} height={340} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis
                type="number"
                dataKey="impact"
                name="Fiscal-block impact"
                tick={{ fontSize: 11, fill: "#64748b" }}
                label={{ value: "fiscal-block impact (summed |news|)", position: "insideBottom", offset: -8, fontSize: 11, fill: "#94a3b8" }}
              />
              <YAxis
                type="number"
                dataKey="gain"
                name="Accuracy gain"
                tick={{ fontSize: 11, fill: "#64748b" }}
                width={44}
                label={{ value: "gain (pp)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
              />
              <ReferenceLine y={0} stroke="#cbd5e1" />
              <Tooltip content={<ScatterTip />} cursor={{ strokeDasharray: "3 3" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Scatter name="Pre-COVID (≤ 2019)" data={pre} fill={PRE} />
              <Scatter name="Post-COVID (≥ 2021)" data={post} fill={POST} />
            </ScatterChart>
          )}
        </ChartFrame>
        <p className="mt-3 text-xs text-slate-500">
          Pre-COVID the fiscal news is tiny and unrelated to accuracy (corr {fmtSigned(s.corr_pre, 2)});
          post-COVID it is several times larger and lines up with the gains (corr{" "}
          {fmtSigned(s.corr_post, 2)}).
        </p>
      </div>

      <div className="card">
        <h3 className="text-base font-semibold text-ink">It is the deficit that carries the signal</h3>
        <p className="mt-1 text-xs text-muted">
          Correlation of each fiscal-block series&apos; impact with the accuracy gain (all non-COVID
          quarters). Only the federal deficit moves with the gains.
        </p>
        <div className="mt-4 space-y-2">
          {byVar.map((v) => {
            const pct = Math.min(100, (Math.abs(v.corr) / 0.5) * 100); // 0.5 corr = full bar
            const isDeficit = v.id === "MTSDS133FMS";
            return (
              <div key={v.id} className="flex items-center gap-3 text-sm">
                <span className="w-40 shrink-0 text-slate-600">{v.label}</span>
                <div className="relative h-3 flex-1 rounded-full bg-slate-100">
                  <div
                    className="absolute left-0 top-0 h-full rounded-full"
                    style={{ width: `${pct}%`, background: isDeficit ? POST : "#cbd5e1" }}
                  />
                </div>
                <span className={`w-12 text-right font-mono ${isDeficit ? "font-semibold text-fiscal" : "text-slate-500"}`}>
                  {fmtSigned(v.corr, 2)}
                </span>
              </div>
            );
          })}
        </div>
        <p className="mt-4 text-xs text-slate-500">
          Government spending (quarterly, slow-moving) and transfer-cleaned income add essentially
          nothing to the gain - consistent with the deficit being the genuine fiscal instrument that
          turned informative under the post-2020 expansionary stance.
        </p>
      </div>
    </div>
  );
}
