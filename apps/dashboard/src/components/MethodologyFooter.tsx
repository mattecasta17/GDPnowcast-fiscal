import { data } from "@/lib/data";

export function MethodologyFooter() {
  const { meta, comparison } = data;
  const leak = comparison.leak_scan;
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <div className="space-y-4 text-sm leading-relaxed text-slate-600">
        <div>
          <h3 className="font-semibold text-ink">The target &amp; the cutoff</h3>
          <p className="mt-1.5">{meta.target_definition}</p>
        </div>
        <div>
          <h3 className="font-semibold text-ink">Why a pre-advance cutoff</h3>
          <p className="mt-1.5">
            On the GDP advance day the BEA also publishes co-releases (real PCE ~68% of GDP, income,
            PCE prices, durable goods). Masking only the GDP cell would leak these into the
            release-week nowcast in most quarters - only {leak.clean_quarters.length} of{" "}
            {leak.quarters} past quarters stay fully clean across the whole release week. Scoring one
            day before the advance removes target and co-release leakage alike.
          </p>
        </div>
      </div>

      <div className="space-y-4 text-sm leading-relaxed text-slate-600">
        <div>
          <h3 className="font-semibold text-ink">Data &amp; panels</h3>
          <p className="mt-1.5">
            Point-in-time vintages from ALFRED/FRED, reconstructed as-of each Friday with{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">realtime_start = realtime_end</code>{" "}
            - no revisions, no fills, observations truncated to the vintage date. The baseline panel
            (<span className="font-mono">{meta.panel_baseline}</span>) and the fiscal panel (
            <span className="font-mono">{meta.panel_fiscal}</span>) share the same calendar and
            target; estimation starts in 2000.
          </p>
        </div>
        <div>
          <h3 className="font-semibold text-ink">Honest research</h3>
          <p className="mt-1.5">
            Every number here is what the corrected, leak-free pipeline actually produces - no
            favourable subsample, no inflated narrative. Where the model has no edge, or the evidence
            is too thin to call, the dashboard says so.
          </p>
        </div>
      </div>
    </div>
  );
}
