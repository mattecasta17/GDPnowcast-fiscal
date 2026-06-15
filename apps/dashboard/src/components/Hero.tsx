import { data } from "@/lib/data";
import { Pill } from "./ui";

export function Hero() {
  const { meta } = data;
  return (
    <div id="top" className="mx-auto max-w-6xl px-5 pb-10 pt-14">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone="blue">Dynamic factor model</Pill>
        <Pill tone="slate">2017 - 2025 &middot; {meta.n_quarters} quarters</Pill>
        <Pill tone="green">Look-ahead safe</Pill>
      </div>
      <h1 className="mt-5 max-w-4xl text-4xl font-bold leading-tight tracking-tight text-ink sm:text-5xl">
        Nowcasting US GDP growth in pseudo real time
      </h1>
      <p className="mt-4 max-w-3xl text-lg leading-relaxed text-slate-600">
        A dynamic factor model reads {meta.n_quarters} quarters of point-in-time data and forecasts
        the BEA <em>advance</em> estimate of real GDP growth at a strict pre-advance cutoff. A
        fiscal-augmented variant and four naive benchmarks are scored on exactly the same target.
      </p>
      <div className="mt-6 rounded-xl border border-line bg-white p-5 shadow-sm">
        <p className="text-sm font-semibold text-ink">The honest takeaway</p>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
          In calm quarters the DFM does <strong>not</strong> beat a simple historical mean on RMSE,
          and the differences are not statistically significant on this short sample. Its real value
          is <strong>robustness in the tails</strong> (it does not blow up in 2020 the way the
          univariate models do) and the <strong>weekly within-quarter path</strong> it produces as
          data arrives. The fiscal block helps only modestly and the evidence is{" "}
          <strong>suggestive, not established</strong>.
        </p>
      </div>
    </div>
  );
}
