// Findings drawn from the "Forecast accuracy across periods" table above.
// Kept qualitative and concise; the figures themselves live in the table.

type ResultFinding = { title: string; body: string; accent: "fiscal" | "slate" };

const FINDINGS: ResultFinding[] = [
  {
    accent: "fiscal",
    title: "The fiscal block improves accuracy outside 2020",
    body: "Excluding the COVID quarters, the Fiscal-enhanced DFM is more accurate than the macro-only Staff Nowcast in every sub-period, on both RMSE and MAE. The gain is modest but consistent.",
  },
  {
    accent: "slate",
    title: "The simplest model wins in normal quarters",
    body: "In normal quarters the historical mean, the simplest model considered, achieves the lowest error of all six. Added factor structure brings no point-accuracy gain in calm quarters.",
  },
];

export function ResultsFindings() {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
      {FINDINGS.map((f) => (
        <div
          key={f.title}
          className={`card relative overflow-hidden pl-6 before:absolute before:left-0 before:top-0 before:h-full before:w-1.5 ${
            f.accent === "fiscal" ? "before:bg-fiscal" : "before:bg-slate-300"
          }`}
        >
          <h3 className="text-base font-semibold text-ink">{f.title}</h3>
          <p className="mt-2 hyphens-auto text-justify text-sm leading-relaxed text-slate-600">
            {f.body}
          </p>
        </div>
      ))}
    </div>
  );
}
