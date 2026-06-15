import { data, fmt } from "@/lib/data";
import { Stat } from "./ui";

export function KpiStrip() {
  const dfmEx = data.benchmarks.metrics.dfm.ex_2020;
  const fiscalEx = data.metrics.fiscal.ex_2020;
  const meanEx = data.benchmarks.metrics.mean.ex_2020;
  const dfmAll = data.benchmarks.metrics.dfm.all;
  const rwAll = data.benchmarks.metrics.rw.all;

  return (
    <div className="mx-auto max-w-6xl px-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="DFM RMSE (ex-2020)"
          value={fmt(dfmEx.rmse)}
          unit="pp"
          accent="baseline"
          sub={`baseline panel, ${dfmEx.n} normal quarters`}
        />
        <Stat
          label="Fiscal RMSE (ex-2020)"
          value={fmt(fiscalEx.rmse)}
          unit="pp"
          accent="fiscal"
          sub="modestly better - but not significant"
        />
        <Stat
          label="Best naive (mean)"
          value={fmt(meanEx.rmse)}
          unit="pp"
          accent="neutral"
          sub="DFM has no RMSE edge in calm times"
        />
        <Stat
          label="Robustness, all 34"
          value={`${fmt(dfmAll.rmse, 1)} vs ${fmt(rwAll.rmse, 1)}`}
          unit="pp"
          accent="neutral"
          sub="DFM vs random walk - univariate blows up on 2020"
        />
      </div>
    </div>
  );
}
