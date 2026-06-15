import { data, fmt, fmtSigned } from "@/lib/data";
import { DeltaChart } from "./DeltaChart";
import { SigBadge } from "./ui";

const LOSS_LABEL: Record<string, string> = { squared: "Squared (MSE)", absolute: "Absolute (MAE)" };

export function ComparisonSection() {
  const dm = data.comparison.diebold_mariano;
  const mdeAbs = data.comparison.power_mde.by_sample.ex_2020.absolute;
  const rows: { sample: "all" | "ex_2020"; loss: "squared" | "absolute" }[] = [
    { sample: "ex_2020", loss: "squared" },
    { sample: "ex_2020", loss: "absolute" },
    { sample: "all", loss: "squared" },
    { sample: "all", loss: "absolute" },
  ];

  return (
    <div className="space-y-6">
      <DeltaChart />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="card overflow-x-auto lg:col-span-3">
          <h3 className="mb-1 text-base font-semibold text-ink">Diebold-Mariano: fiscal vs baseline</h3>
          <p className="mb-3 text-xs text-muted">
            Negative stat = fiscal more accurate. h=1; the HLN small-sample stat equals a paired
            t-test here.
          </p>
          <table className="w-full min-w-[520px] text-sm">
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
              {rows.map(({ sample, loss }) => {
                const c = dm[sample][loss];
                return (
                  <tr key={`${sample}-${loss}`} className="border-b border-line/70 text-slate-700">
                    <td className="py-2 pr-3 font-sans">{sample === "ex_2020" ? "ex-2020" : "all 34"}</td>
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
          <h3 className="text-base font-semibold text-ink">Is the sample big enough?</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            The one significant cell (ex-2020 MAE, p={fmt(dm.ex_2020.absolute.p_value, 3)}) is still{" "}
            <strong>underpowered</strong>: the observed effect is smaller than the minimum this
            34-quarter sample can reliably detect at 80% power.
          </p>
          <dl className="mt-4 space-y-2 text-sm">
            <Row k="Observed |effect| (MAE)" v={`${fmt(Math.abs(mdeAbs.mean_loss_diff), 3)} pp`} />
            <Row k="Min. detectable effect" v={`${fmt(mdeAbs.mde, 3)} pp`} />
            <Row k="Powered?" v={mdeAbs.powered ? "yes" : "no"} bad={!mdeAbs.powered} />
          </dl>
          <p className="mt-4 text-xs text-slate-500">
            One p=0.036 across four tests also fails a Bonferroni correction (~0.14). The fiscal edge
            is real-looking but <strong>suggestive, not established</strong>.
          </p>
        </div>
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
