import { data, fiscalWinCounts, fmt, fmtSigned } from "@/lib/data";
import { Stat } from "./ui";

export function KpiStrip() {
  const staffEx = data.metrics.baseline.ex_2020;
  const fiscalEx = data.metrics.fiscal.ex_2020;
  const dfmAll = data.benchmarks.metrics.dfm.all;
  const rwAll = data.benchmarks.metrics.rw.all;
  const fi = data.fiscal_impact.summary;
  const { wins, n } = fiscalWinCounts();

  return (
    <div className="mx-auto max-w-6xl px-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Fiscal-enhanced RMSE (ex-2020)"
          value={fmt(fiscalEx.rmse)}
          unit="pp"
          accent="fiscal"
          sub={`vs Staff Nowcast ${fmt(staffEx.rmse)} - lower on ${wins}/${n} quarters`}
        />
        <Stat
          label="Fiscal news, post-COVID"
          value={`${fmt(fi.impact_ratio_post_pre, 1)}×`}
          accent="fiscal"
          sub="bigger fiscal surprises than pre-2020"
        />
        <Stat
          label="Impact ↔ accuracy gain"
          value={fmtSigned(fi.corr_post, 2)}
          accent="fiscal"
          sub="post-COVID correlation, deficit-driven"
        />
        <Stat
          label="DFM robustness, all 34"
          value={`${fmt(dfmAll.rmse, 1)} vs ${fmt(rwAll.rmse, 1)}`}
          unit="pp"
          accent="neutral"
          sub="Staff Nowcast vs random walk - univariate blows up on 2020"
        />
      </div>
    </div>
  );
}
