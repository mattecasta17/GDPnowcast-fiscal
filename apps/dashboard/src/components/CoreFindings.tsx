// The section's four findings, stated up front; the charts below document each in turn.
// All numbers derive from the committed data bundle, not hand-typed copy.

import { data, fmt, fmtSigned } from "@/lib/data";

const s = data.fiscal_impact.summary;
const ablP = (id: string) =>
  data.ablation.models.find((m) => m.id === id)?.dm_vs_macro?.absolute.p ?? 0;

type Finding = { title: string; body: string; accent: "fiscal" | "slate" };

const FINDINGS: Finding[] = [
  {
    accent: "fiscal",
    title: "The fiscal signal switches on after 2020",
    body:
      `Fiscal news averages ${fmt(s.mean_impact_pre, 2)} pp per quarter before COVID and ` +
      `${fmt(s.mean_impact_post, 2)} pp after, a ${fmt(s.impact_ratio_post_pre, 1)}-fold ` +
      `increase. The accuracy gain over the Staff Nowcast scales with the size of this news: ` +
      `correlation ${fmtSigned(s.corr_post, 2)} post-2020 against ${fmtSigned(s.corr_pre, 2)} before.`,
  },
  {
    accent: "fiscal",
    title: "The federal deficit carries most of the signal",
    body:
      `Of the three fiscal series, only the deficit's news co-moves with the quarter-by-quarter ` +
      `gain (correlation ${fmtSigned(s.corr_by_variable["MTSDS133FMS"], 2)}; government spending ` +
      `and income excluding transfers near zero). Its signed surprises track the growth the ` +
      `macro panel leaves unexplained, with the correct sign.`,
  },
  {
    accent: "fiscal",
    title: "The block matters more than any single series",
    body:
      `Re-estimated on the same data, the deficit alone does not significantly improve on the ` +
      `macro panel (p=${fmt(ablP("deficit"), 2)}); adding income excluding transfers brings the ` +
      `model to significance (p=${fmt(ablP("deficit_income"), 3)}). Consistent with Stock and ` +
      `Watson (2002), series with modest individual signal sharpen the common factor collectively.`,
  },
  {
    accent: "slate",
    title: "The evidence is predictive, not causal",
    body:
      `The deficit's news improves the nowcast because it is a fast, correctly-signed indicator ` +
      `of growth the macro panel misses. A forecasting design of this kind does not separate the ` +
      `deficit's causal contribution to growth from its role as an early measure of it.`,
  },
];

export function CoreFindings() {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
      {FINDINGS.map((f, i) => (
        <div
          key={f.title}
          className={`card relative overflow-hidden pl-6 before:absolute before:left-0 before:top-0 before:h-full before:w-1.5 ${
            f.accent === "fiscal" ? "before:bg-fiscal" : "before:bg-slate-300"
          }`}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Finding {i + 1}</p>
          <h3 className="mt-1 text-base font-semibold text-ink">{f.title}</h3>
          <p className="mt-2 hyphens-auto text-justify text-sm leading-relaxed text-slate-600">
            {f.body}
          </p>
        </div>
      ))}
    </div>
  );
}
