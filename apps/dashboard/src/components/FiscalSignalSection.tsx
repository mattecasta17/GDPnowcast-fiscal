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

const POST = COLORS.fiscal;
const PRE = "#94a3b8";

type Pt = { period: string; x: number; y: number };

function ScatterTip({ active, payload }: { active?: boolean; payload?: { payload: Pt }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-semibold text-ink">{periodLabel(p.period)}</p>
      <p className="mt-0.5 text-slate-600">
        deficit news <span className="font-mono text-ink">{fmtSigned(p.x, 2)}</span>
      </p>
      <p className="text-slate-600">
        growth missed by macro <span className="font-mono text-ink">{fmtSigned(p.y, 2)} pp</span>
      </p>
    </div>
  );
}

export function FiscalSignalSection() {
  const fi = data.fiscal_impact;
  const s = fi.summary;
  const sg = s.signed;
  const dp = sg.decomposition_post;

  const pts: Pt[] = fi.per_quarter.map((r) => ({
    period: r.period,
    x: r.signed_deficit,
    y: r.resid_vs_staff,
  }));
  const pre = pts.filter((p) => Number(p.period.slice(0, 4)) <= 2019);
  const post = pts.filter((p) => Number(p.period.slice(0, 4)) >= 2021);

  // Post-2020 OLS fit line (residual axis), drawn across the post-COVID x-range.
  const xs = post.map((p) => p.x);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const { slope, intercept } = sg.resid.fit_post;
  const fitSeg = [
    { x: xMin, y: slope * xMin + intercept },
    { x: xMax, y: slope * xMax + intercept },
  ];

  const decomp = [
    {
      label: "Deficit signal and realized growth",
      corr: dp.deficit_vs_growth,
      read: "the deficit revision moves with growth",
      key: false,
    },
    {
      label: "Macro-only nowcast and realized growth",
      corr: dp.macro_vs_growth,
      read: "the macro panel alone barely tracks post-2020 growth",
      key: false,
    },
    {
      label: "Deficit signal and macro-only nowcast",
      corr: dp.deficit_vs_macro,
      read: "the deficit signal is nearly orthogonal to the macro signal",
      key: false,
    },
    {
      label: "Deficit signal and growth unexplained by macro",
      corr: dp.deficit_vs_resid,
      read: `it tracks what the macro model misses (incremental, p=${fmt(dp.deficit_vs_resid.p, 2)})`,
      key: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="text-base font-semibold text-ink">
          The deficit surprise and the growth the macro model misses
        </h3>
        <p className="mb-4 text-xs text-muted">
          Each point is a non-COVID quarter. The horizontal axis is the signed deficit news: the
          revision the federal deficit imparts to the GDP nowcast, positive when a larger-than-expected
          deficit raises the nowcast. The vertical axis is the growth the macro-only Staff Nowcast
          leaves unexplained, the realized advance growth minus the Staff Nowcast. The dashed line is
          the post-2020 ordinary-least-squares fit.
        </p>
        <ChartFrame height={340}>
          {(w) => (
            <ScatterChart width={w} height={340} margin={{ top: 8, right: 16, left: 0, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis
                type="number"
                dataKey="x"
                name="Signed deficit news"
                tick={{ fontSize: 11, fill: "#64748b" }}
                label={{ value: "signed deficit news (pp)", position: "insideBottom", offset: -8, fontSize: 11, fill: "#94a3b8" }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Growth missed by macro"
                tick={{ fontSize: 11, fill: "#64748b" }}
                width={48}
                label={{ value: "realized - macro (pp)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
              />
              <ReferenceLine x={0} stroke="#e2e8f0" />
              <ReferenceLine y={0} stroke="#cbd5e1" />
              <ReferenceLine
                segment={fitSeg}
                stroke={POST}
                strokeWidth={1.5}
                strokeDasharray="5 4"
                ifOverflow="extendDomain"
              />
              <Tooltip content={<ScatterTip />} cursor={{ strokeDasharray: "3 3" }} />
              <Legend verticalAlign="top" align="right" height={24} wrapperStyle={{ fontSize: 12 }} />
              <Scatter name="Pre-COVID (≤ 2019)" data={pre} fill={PRE} />
              <Scatter name="Post-COVID (≥ 2021)" data={post} fill={POST} />
            </ScatterChart>
          )}
        </ChartFrame>
        <p className="mt-3 text-xs text-slate-500">
          Before 2020 the deficit news is near zero and unrelated to the macro residual (correlation{" "}
          {fmtSigned(sg.resid.pre.r, 2)}). After 2020 the deficit news is systematically larger and
          lines up with the residual growth surprises (correlation {fmtSigned(sg.resid.post.r, 2)},
          p={fmt(sg.resid.post.p, 2)}).
        </p>
        <p className="mt-3 border-l-2 border-line pl-3 text-xs text-slate-500">
          This is a predictive association. The deficit&apos;s surprises track realized growth and
          sharpen the nowcast, but a forecasting model of this kind does not separate the
          deficit&apos;s causal contribution to growth from its role as a fast, well-measured indicator
          of it.
        </p>
      </div>

      <div className="card">
        <h3 className="text-base font-semibold text-ink">
          Isolating the deficit&apos;s incremental contribution
        </h3>
        <p className="mt-1 text-xs text-muted">All correlations are post-COVID (n=18).</p>
        <table className="mt-3 w-full text-sm">
          <tbody>
            {decomp.map((d) => (
              <tr key={d.label} className="border-t border-line first:border-0">
                <td className="py-2 pr-3 text-slate-600">{d.label}</td>
                <td
                  className={`w-14 py-2 pr-4 text-right font-mono ${d.key ? "font-semibold text-fiscal" : "text-ink"}`}
                >
                  {fmtSigned(d.corr.r, 2)}
                </td>
                <td className="hidden py-2 text-xs text-muted sm:table-cell">{d.read}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <details className="mt-4">
          <summary className="cursor-pointer text-xs font-medium text-slate-600 hover:text-ink">
            Methodological note: why the residual is the right test
          </summary>
          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            The raw correlation between the deficit signal and realized growth (+0.53) overstates the
            deficit&apos;s value, because any nowcast revision tends to comove with its target. The
            relevant question is whether the deficit explains variation the macro-only model leaves
            unexplained. Two features make the contribution genuinely incremental rather than
            redundant. First, the macro-only nowcast is nearly uninformative about post-2020 growth
            (correlation 0.12): the standard macro panel did not anticipate the post-pandemic
            surprises. Second, the deficit signal is almost orthogonal to the macro nowcast
            (correlation 0.13), so it does not restate information already in the panel. Net of what
            the macro model captures, the deficit signal still tracks the residual growth surprises
            (correlation 0.38), though on eighteen quarters this incremental association is suggestive
            rather than significant (p=0.12).
          </p>
        </details>

        <p className="mt-4 border-l-2 border-line pl-3 text-xs text-slate-500">
          The association is concentrated in the high-deficit quarters of 2021-2022 and is not robust
          to excluding them; on a short sample it should be read as suggestive.
        </p>
      </div>

    </div>
  );
}
