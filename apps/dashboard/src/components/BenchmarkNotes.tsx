const BENCHMARKS: { name: string; text: string }[] = [
  {
    name: "Historical mean",
    text: "Forecasts each quarter as the average growth observed up to that point. It has no dynamics and uses no indicators, providing the unconditional-mean baseline.",
  },
  {
    name: "Random walk",
    text: "Sets the forecast equal to the most recent realized quarter, the standard naive benchmark in macroeconomic forecasting.",
  },
  {
    name: "AR(1)",
    text: "A first-order autoregression of GDP growth on its own previous value and a constant, the simplest specification with genuine dynamics.",
  },
  {
    name: "ARMA(1,1)",
    text: "Adds a moving-average term to the AR(1), so that both the previous level and the previous shock enter the forecast.",
  },
];

export function BenchmarkNotes() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {BENCHMARKS.map((b) => (
        <div key={b.name} className="card">
          <h4 className="text-sm font-semibold text-ink">{b.name}</h4>
          <p className="mt-1.5 hyphens-auto text-justify text-sm leading-relaxed text-slate-600">
            {b.text}
          </p>
        </div>
      ))}
    </div>
  );
}
