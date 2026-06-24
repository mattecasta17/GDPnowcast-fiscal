import { data, fmt, fmtSigned } from "@/lib/data";
import { SigBadge } from "./ui";

const LOSS_LABEL: Record<string, string> = {
  squared: "Squared (MSE)",
  absolute: "Absolute (MAE)",
};

const PERIODS: { key: "ex_2020" | "pre" | "post"; label: string }[] = [
  { key: "ex_2020", label: "Full Sample ex Covid" },
  { key: "pre", label: "Pre-COVID" },
  { key: "post", label: "Post-COVID" },
];

export function ComparisonSection() {
  const dm = data.comparison.dm_by_period;
  const mdeAbs = data.comparison.power_mde.by_sample.ex_2020.absolute;

  const rows: { period: (typeof PERIODS)[number]; loss: "squared" | "absolute" }[] = [];
  for (const period of PERIODS) {
    for (const loss of ["squared", "absolute"] as const) rows.push({ period, loss });
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <div className="card overflow-x-auto lg:col-span-3">
        <h3 className="mb-1 text-base font-semibold text-ink">
          Diebold-Mariano: <span className="text-fiscal">Fiscal-enhanced</span> vs{" "}
          <span className="text-baseline">Staff Nowcast</span>
        </h3>
        <p className="mb-3 text-xs text-muted">
          A negative statistic means the Fiscal-enhanced DFM is the more accurate of the two. The
          test uses quarterly losses at h=1, where the Harvey-Leybourne-Newbold small-sample
          statistic coincides with a paired t-test.
        </p>
        <table className="w-full min-w-[540px] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="py-2 pr-3 font-medium">Sample</th>
              <th className="px-3 py-2 font-medium">Loss</th>
              <th className="px-3 py-2 text-right font-medium">DM stat</th>
              <th className="px-3 py-2 text-right font-medium">p-value</th>
              <th className="px-3 py-2 text-right font-medium">mean &Delta;loss</th>
              <th className="px-3 py-2 text-center font-medium">5%</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {rows.map(({ period, loss }) => {
              const c = dm[period.key][loss];
              return (
                <tr
                  key={`${period.key}-${loss}`}
                  className="border-b border-line/70 text-slate-700"
                >
                  <td className="py-2 pr-3 font-sans">{period.label}</td>
                  <td className="px-3 py-2 font-sans text-xs">{LOSS_LABEL[loss]}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmt(c.dm_stat)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmt(c.p_value, 3)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtSigned(c.mean_loss_diff, 3)}</td>
                  <td className="px-3 py-2 text-center">
                    <SigBadge p={c.p_value} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="card lg:col-span-2">
        <h3 className="text-base font-semibold text-ink">Power and sample size</h3>
        <p className="mt-2 hyphens-auto text-justify text-sm leading-relaxed text-slate-600">
          With thirty non-COVID quarters the test can reliably detect, at 80% power, only effects
          larger than about {fmt(mdeAbs.mde, 2)} pp, while the measured gain is about{" "}
          {fmt(Math.abs(mdeAbs.mean_loss_diff), 2)} pp. The sample is therefore too short to certify
          an effect of this size, even though every test points in the model&apos;s favour.
        </p>
        <dl className="mt-4 space-y-2 text-sm">
          <Row k="Observed |effect| (MAE)" v={`${fmt(Math.abs(mdeAbs.mean_loss_diff), 3)} pp`} />
          <Row k="Min. detectable effect" v={`${fmt(mdeAbs.mde, 3)} pp`} />
          <Row k="Powered?" v={mdeAbs.powered ? "yes" : "no"} bad={!mdeAbs.powered} />
        </dl>
        <p className="mt-4 hyphens-auto text-justify text-xs text-slate-500">
          With one significant cell among the six tests, the result does not survive a
          multiple-testing correction. It is best read as consistent, economically coherent evidence
          awaiting a longer sample, rather than an established effect.
        </p>
      </div>
    </div>
  );
}

function Row({ k, v, bad }: { k: string; v: string; bad?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-line/60 pb-2">
      <dt className="text-slate-600">{k}</dt>
      <dd className={`font-mono font-medium ${bad ? "text-red-600" : "text-ink"}`}>{v}</dd>
    </div>
  );
}
