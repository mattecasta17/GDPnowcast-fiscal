import { COLORS, data, fmtSigned } from "@/lib/data";

// F5a -- which fiscal series the quarter-to-quarter gain actually tracks. Static (no chart lib).

const POST = COLORS.fiscal;

const fi = data.fiscal_impact;
const s = fi.summary;
const byVar = fi.fiscal_block.map((v) => ({ ...v, corr: s.corr_by_variable[v.id] ?? 0 }));

export function DeficitGainBars() {
  return (
    <div className="card">
      <h3 className="text-base font-semibold text-ink">
        The quarter-to-quarter gain co-moves only with the deficit
      </h3>
      <p className="mt-1 text-xs text-muted">
        Correlation between each fiscal-block series&apos; news and the quarter-by-quarter accuracy
        gain, across all non-COVID quarters. Only the federal deficit&apos;s news moves with the gain.
      </p>
      <div className="mt-4 space-y-2">
        {byVar.map((v) => {
          const pct = Math.min(100, (Math.abs(v.corr) / 0.5) * 100); // 0.5 corr = full bar
          const isDeficit = v.id === "MTSDS133FMS";
          return (
            <div key={v.id} className="flex items-center gap-3 text-sm">
              <span className="w-40 shrink-0 text-slate-600">{v.label}</span>
              <div className="relative h-3 flex-1 rounded-full bg-slate-100">
                <div
                  className="absolute left-0 top-0 h-full rounded-full"
                  style={{ width: `${pct}%`, background: isDeficit ? POST : "#cbd5e1" }}
                />
              </div>
              <span
                className={`w-12 text-right font-mono ${isDeficit ? "font-semibold text-fiscal" : "text-slate-500"}`}
              >
                {fmtSigned(v.corr, 2)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-xs text-slate-500">
        These correlations describe the timing of the gain, not each series&apos; contribution to
        overall accuracy. The deficit&apos;s news is what moves the nowcast quarter by quarter; income
        excluding transfers and government spending barely register here. Their contribution to average
        accuracy is a distinct question, taken up in the ablation below, where income excluding
        transfers turns out to matter.
      </p>
    </div>
  );
}
