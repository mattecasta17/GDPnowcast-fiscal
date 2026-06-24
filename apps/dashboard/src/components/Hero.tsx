export function Hero() {
  return (
    <div id="top" className="mx-auto max-w-6xl px-5 pb-10 pt-14">
      <h1 className="text-center text-4xl font-bold leading-tight tracking-tight text-ink">
        <span className="block">Improving GDP Nowcasting Using Fiscal Variables:</span>
        <span className="block">Evidence from a Dynamic Factor Model</span>
      </h1>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-ink">Introduction</h2>
        <p className="mt-2 text-lg leading-relaxed text-slate-600 text-justify hyphens-auto">
          The New York Fed Staff Nowcast, one of the best-known dynamic factor models for nowcasting
          GDP, produces its estimate from macroeconomic variables alone. This study examines whether
          augmenting such a model with fiscal variables improves the nowcast.
        </p>
      </div>

      <div className="mt-6">
        <h2 className="text-xl font-semibold text-ink">Methodology</h2>
        <p className="mt-2 text-lg leading-relaxed text-slate-600 text-justify hyphens-auto">
          To test this, two dynamic factor models are estimated. The first is a macro-only
          specification that closely replicates the New York Fed Staff Nowcast and uses the same
          variables; the second adds a block of government-finance series (the federal deficit,
          government spending, and income excluding transfers). Both are backtested over
          2017&ndash;2025. Each quarter&apos;s nowcast is produced faithfully from point-in-time
          vintage data from ALFRED and runs for 22 weeks, updating as new releases arrive and
          stopping when the BEA advance estimate is published. The results are compared both between
          the two models and against four traditional univariate models used as benchmarks.
        </p>
      </div>
    </div>
  );
}
