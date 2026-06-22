import { data } from "@/lib/data";
import { Pill } from "./ui";

export function Hero() {
  const { meta } = data;
  return (
    <div id="top" className="mx-auto max-w-6xl px-5 pb-10 pt-14">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone="blue">Fiscal vs macro DFM</Pill>
        <Pill tone="slate">2017 - 2025 &middot; {meta.n_quarters} quarters</Pill>
        <Pill tone="green">Look-ahead safe</Pill>
      </div>
      <h1 className="mt-5 max-w-4xl text-4xl font-bold leading-tight tracking-tight text-ink sm:text-5xl">
        Does a fiscal block sharpen a real-time GDP nowcast?
      </h1>
      <p className="mt-4 max-w-3xl text-lg leading-relaxed text-slate-600">
        Two dynamic factor models race on the same target: a macro-only{" "}
        <strong className="text-baseline">Staff Nowcast</strong> and a{" "}
        <strong className="text-fiscal">Fiscal-enhanced DFM</strong> that adds a block of
        government-finance series on top of it. Both forecast the BEA <em>advance</em> estimate of
        real GDP growth at a strict pre-advance cutoff; four traditional benchmarks set the bar.
      </p>
      <div className="mt-6 rounded-xl border border-line bg-white p-5 shadow-sm">
        <p className="text-sm font-semibold text-ink">The honest takeaway</p>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
          The fiscal block <strong>helps</strong> - modestly, in a majority of quarters, and most
          clearly <strong>after 2020</strong>, when deficit surprises ballooned and started moving
          with the accuracy gains. But on {meta.n_quarters} quarters the edge is{" "}
          <strong>suggestive, not statistically established</strong>. Both factor models share one
          real advantage over the traditional benchmarks: in calm times they are only mid-pack on
          precision, but they <strong>do not blow up in the tails</strong> the way the univariate
          models do in 2020.
        </p>
      </div>
    </div>
  );
}
