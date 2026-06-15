import { data, fmt, fmtSigned, MODEL_LABELS } from "@/lib/data";
import { BenchmarkChart } from "./BenchmarkChart";
import { Pill } from "./ui";

const ORDER = ["dfm", "mean", "rw", "ar1", "arma11"];

function countSigDM(): { sig: number; total: number } {
  let sig = 0;
  let total = 0;
  for (const m of ["mean", "rw", "ar1", "arma11"]) {
    for (const s of ["all", "ex_2020"] as const) {
      for (const l of ["squared", "absolute"] as const) {
        total += 1;
        if (data.benchmarks.diebold_mariano[m][s][l].p_value < 0.05) sig += 1;
      }
    }
  }
  return { sig, total };
}

export function BenchmarkSection() {
  const { sig, total } = countSigDM();
  return (
    <div className="space-y-6">
      <BenchmarkChart />

      <div className="card overflow-x-auto">
        <h3 className="mb-3 text-base font-semibold text-ink">Accuracy table (pp)</h3>
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="py-2 pr-3 font-medium">Model</th>
              <th className="px-3 py-2 text-right font-medium">RMSE ex-2020</th>
              <th className="px-3 py-2 text-right font-medium">MAE ex-2020</th>
              <th className="px-3 py-2 text-right font-medium">Bias ex-2020</th>
              <th className="px-3 py-2 text-right font-medium">RMSE all</th>
              <th className="px-3 py-2 text-right font-medium">MAE all</th>
              <th className="px-3 py-2 text-right font-medium">Bias all</th>
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {ORDER.map((m) => {
              const ex = data.benchmarks.metrics[m].ex_2020;
              const all = data.benchmarks.metrics[m].all;
              const isDfm = m === "dfm";
              return (
                <tr
                  key={m}
                  className={`border-b border-line/70 ${isDfm ? "bg-blue-50/60 font-semibold text-ink" : "text-slate-700"}`}
                >
                  <td className="py-2 pr-3 font-sans">{MODEL_LABELS[m]}</td>
                  <td className="px-3 py-2 text-right">{fmt(ex.rmse)}</td>
                  <td className="px-3 py-2 text-right">{fmt(ex.mae)}</td>
                  <td className="px-3 py-2 text-right">{fmtSigned(ex.bias)}</td>
                  <td className="px-3 py-2 text-right">{fmt(all.rmse)}</td>
                  <td className="px-3 py-2 text-right">{fmt(all.mae)}</td>
                  <td className="px-3 py-2 text-right">{fmtSigned(all.bias)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-600">
          <Pill tone="slate">
            Diebold-Mariano: {sig}/{total} significant
          </Pill>
          <span>
            Not one of the {total} DFM-vs-benchmark tests (h=1, both losses, both samples) rejects at
            5% - the models are statistically indistinguishable on this 34-quarter sample.
          </span>
        </div>
        <p className="mt-3 text-xs text-slate-500">{data.benchmarks.gdpnow_note}</p>
      </div>
    </div>
  );
}
