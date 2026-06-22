import { data, fmt } from "@/lib/data";

type ModelCard = {
  id: string;
  name: string;
  what: string;
  why: string;
};

const MODELS: ModelCard[] = [
  {
    id: "mean",
    name: "Historical mean",
    what: "Forecasts every quarter as the average growth rate seen so far. No dynamics, no inputs - just the unconditional mean.",
    why: "The most basic 'can you beat doing nothing clever?' bar. Surprisingly hard to beat for a stable, mean-reverting series like quarterly GDP growth.",
  },
  {
    id: "rw",
    name: "Random walk",
    what: "Forecasts next quarter as equal to the last realized quarter ('no change'). The canonical naive forecast in macro and finance.",
    why: "The textbook benchmark a forecast must beat to claim any skill. It tracks persistence but lurches badly around turning points.",
  },
  {
    id: "ar1",
    name: "AR(1)",
    what: "A first-order autoregression on past GDP growth: this quarter is a fitted fraction of last quarter plus a constant.",
    why: "A minimal time-series model with real (if thin) dynamics - the simplest thing that is more than a naive rule.",
  },
  {
    id: "arma11",
    name: "ARMA(1,1)",
    what: "Adds a moving-average term to the AR(1), letting last quarter's shock as well as its level feed the forecast.",
    why: "A slightly richer univariate model. If a factor model cannot beat this, the multivariate machinery is not buying accuracy in calm times.",
  },
];

export function TraditionalModelsSection() {
  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="text-base font-semibold text-ink">Why include traditional benchmarks at all?</h3>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
          A nowcast is only impressive relative to a baseline. These four univariate models forecast
          GDP growth from its own past alone - no monthly indicators, no fiscal data. They set the bar
          the dynamic factor models have to clear: if a 30-variable DFM cannot beat a one-line random
          walk, the extra structure is not earning its keep. The honest result here is that in calm
          quarters it does not beat them on point accuracy - the DFM&apos;s payoff is robustness in
          the tails and the weekly within-quarter path, neither of which a single-number model can
          give you.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {MODELS.map((m) => {
          const ex = data.benchmarks.metrics[m.id]?.ex_2020;
          const all = data.benchmarks.metrics[m.id]?.all;
          return (
            <div key={m.id} className="card flex flex-col">
              <div className="flex items-baseline justify-between gap-3">
                <h4 className="text-sm font-semibold text-ink">{m.name}</h4>
                {ex && all ? (
                  <span className="font-mono text-xs text-slate-500">
                    RMSE {fmt(ex.rmse, 1)} ex-2020 · {fmt(all.rmse, 1)} all
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{m.what}</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">
                <span className="font-medium text-slate-600">Why it&apos;s a fair test: </span>
                {m.why}
              </p>
            </div>
          );
        })}
      </div>

      <div className="card border-amber-200 bg-amber-50/40">
        <h4 className="text-sm font-semibold text-ink">Why not the Atlanta Fed&apos;s GDPNow?</h4>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{data.benchmarks.gdpnow_note}</p>
      </div>
    </div>
  );
}
