import type { ReactNode } from "react";
import { data, fmt } from "@/lib/data";

// F0 -- the conceptual setup for the whole section: what a "news" is and how it moves the nowcast.
// Static (no chart), so it stays a server component.

const ex = data.fiscal_impact.per_quarter.find((r) => r.period === "2021q2");
const exDeficit = ex ? ex.per_variable["MTSDS133FMS"] ?? 0 : 0;

type Step = { tag: string; sym: ReactNode; note: string };

const STEPS: Step[] = [
  { tag: "Prior projection", sym: <>x&thinsp;<sup>old</sup></>, note: "what the model expected the series to be" },
  { tag: "New release", sym: <>x&thinsp;<sup>new</sup></>, note: "the value actually published" },
  { tag: "News (surprise)", sym: <>x&thinsp;<sup>new</sup> &minus; x&thinsp;<sup>old</sup></>, note: "the part the model did not anticipate" },
  { tag: "Nowcast revision", sym: <>&Delta;&yacute;</>, note: "how much the GDP nowcast moves" },
];

export function FiscalNewsInfographic() {
  return (
    <div className="card">
      <h3 className="text-base font-semibold text-ink">How a release moves the nowcast</h3>
      <p className="mt-1 text-xs text-muted">
        The dynamic factor model reads each fiscal release as <em>news</em>: the gap between the
        published value and the value the model had projected. Only that surprise moves the nowcast.
      </p>

      <div className="mt-5 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
        {STEPS.map((s, i) => (
          <div key={s.tag} className="flex flex-col items-stretch gap-2 sm:flex-1 sm:flex-row sm:items-center">
            <div
              className={`flex-1 rounded-lg border px-3 py-2.5 text-center ${
                i === 2
                  ? "border-fiscal/40 bg-fiscal/5"
                  : i === 3
                    ? "border-line bg-slate-50"
                    : "border-line bg-white"
              }`}
            >
              <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{s.tag}</div>
              <div className="mt-1 font-mono text-sm text-ink">{s.sym}</div>
              <div className="mt-1 text-[11px] leading-tight text-muted">{s.note}</div>
            </div>
            {i < STEPS.length - 1 && (
              <div className="flex shrink-0 items-center justify-center sm:px-0.5">
                <span className="rotate-90 text-slate-300 sm:rotate-0">&rarr;</span>
                {i === 2 && (
                  <span className="ml-1 hidden text-[10px] text-slate-400 sm:inline">&times; gain</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-x-6 gap-y-2 border-t border-line pt-4 text-xs text-slate-500 sm:grid-cols-2">
        <p>
          <span className="font-mono text-ink">news = x&thinsp;<sup>new</sup> &minus; x&thinsp;<sup>old</sup></span>
          <span className="ml-2 text-slate-400">(eq. 12)</span>
        </p>
        <p>
          <span className="font-mono text-ink">impact = &lambda;&prime;<sub>y</sub> A&thinsp;<sup>h</sup> K &middot; news</span>
          <span className="ml-2 text-slate-400">(eq. 13)</span>
        </p>
      </div>

      <p className="mt-4 border-l-2 border-fiscal/50 pl-3 text-xs text-slate-600">
        2021 Q2 &mdash; the federal deficit printed well above the model&apos;s projection; that single
        surprise added <span className="font-mono text-fiscal">+{fmt(exDeficit, 2)} pp</span> to the GDP
        nowcast.
      </p>

      <p className="mt-3 text-xs text-muted">
        A large news means the release lands far from the model&apos;s projection &mdash; the series is
        surprising the model. The fiscal block helps only insofar as it springs such surprises, which,
        as the next charts show, it does mostly through the deficit and mostly after 2020.
      </p>
    </div>
  );
}
