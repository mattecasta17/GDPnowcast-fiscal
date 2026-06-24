"use client";

import { data, fmt } from "@/lib/data";

export function AblationSection() {
  const abl = data.ablation;
  const by = (id: string) => abl.models.find((m) => m.id === id);
  const pDeficit = by("deficit")?.dm_vs_macro?.absolute.p;
  const pDefInc = by("deficit_income")?.dm_vs_macro?.absolute.p;

  return (
    <div className="card">
      <h3 className="text-base font-semibold text-ink">Which fiscal series the model needs</h3>
      <p className="mt-1 text-xs text-muted">
        Each row adds fiscal series to the shared macro panel and re-estimates the DFM on the same
        data. RMSE and MAE are the headline (advance-1) errors, ex-2020 (n={abl.n_ex_2020}). The last
        column tests each model against the macro-only Staff Nowcast (Diebold-Mariano on MAE).
      </p>
      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="text-xs text-muted">
            <th className="py-1 text-left font-medium">Model</th>
            <th className="py-1 text-right font-medium">RMSE</th>
            <th className="py-1 text-right font-medium">MAE</th>
            <th className="py-1 text-right font-medium">vs macro</th>
          </tr>
        </thead>
        <tbody>
          {abl.models.map((m) => {
            const best = m.id === "all";
            const p = m.dm_vs_macro?.absolute.p;
            const sig = p !== undefined && p < 0.05;
            return (
              <tr key={m.id} className="border-t border-line">
                <td className={`py-2 ${best ? "font-semibold text-fiscal" : "text-slate-700"}`}>
                  {m.label}
                </td>
                <td className="py-2 text-right font-mono text-ink">{fmt(m.rmse, 3)}</td>
                <td className="py-2 text-right font-mono text-ink">{fmt(m.mae, 3)}</td>
                <td className="py-2 text-right font-mono text-xs">
                  {p === undefined ? (
                    <span className="text-slate-400">&mdash;</span>
                  ) : sig ? (
                    <span className="font-semibold text-fiscal">p={fmt(p, 3)}</span>
                  ) : (
                    <span className="text-slate-400">p={fmt(p, 2)}</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-4 text-xs text-slate-500">
        The deficit alone does not significantly improve on the macro panel (p={fmt(pDeficit ?? 0, 2)}
        ). Adding income excluding transfers produces the largest single improvement and brings the
        model to significance against the macro-only nowcast (p={fmt(pDefInc ?? 0, 2)}), although that
        series taken on its own barely correlates with the quarter-to-quarter gain. Government spending
        is redundant. This follows the dynamic-factor logic of Stock and Watson (2002): indicators with
        only modest individual co-movement with the cycle still sharpen the estimated common factor
        collectively, so the full fiscal block outperforms any single series.
      </p>
      <p className="mt-3 border-l-2 border-line pl-3 text-xs text-slate-500">
        On thirty quarters these differences are small; the ranking is descriptive and the move into
        significance is suggestive rather than established.
      </p>
    </div>
  );
}
