import { BenchmarkSection } from "@/components/BenchmarkSection";
import { ComparisonSection } from "@/components/ComparisonSection";
import { FindingsSection } from "@/components/FindingsSection";
import { HeadlineChart } from "@/components/HeadlineChart";
import { Hero } from "@/components/Hero";
import { KpiStrip } from "@/components/KpiStrip";
import { MethodologyFooter } from "@/components/MethodologyFooter";
import { Nav } from "@/components/Nav";
import { QuarterErrorChart } from "@/components/QuarterErrorChart";
import { Section } from "@/components/ui";
import { WeeklyExplorer } from "@/components/WeeklyExplorer";

export default function Home() {
  return (
    <>
      <Nav />
      <Hero />
      <KpiStrip />

      <Section
        id="headline"
        eyebrow="Headline"
        title="Nowcast vs the BEA advance"
        intro="One point per quarter: the model's pre-advance forecast against the number the BEA actually printed first. The baseline and fiscal variants track the advance closely in calm quarters and miss the genuine real-economy surprises (2022, 2025q1)."
      >
        <div className="space-y-6">
          <HeadlineChart />
          <QuarterErrorChart />
        </div>
      </Section>

      <Section
        id="weekly"
        eyebrow="Within-quarter"
        title="The weekly nowcast path"
        intro="This is what a factor model gives you that a single-number benchmark cannot: a forecast that updates every week as new data is released, converging toward the eventual advance. Pick any quarter and watch it move."
      >
        <WeeklyExplorer />
      </Section>

      <Section
        id="benchmarks"
        eyebrow="Benchmarks"
        title="DFM vs naive models"
        intro="The honest test: does the dynamic factor model actually beat a historical mean, a random walk, or a small ARMA fit to past GDP growth? In normal times, no - it is mid-pack. Across the full sample including 2020, it is far more robust."
      >
        <BenchmarkSection />
      </Section>

      <Section
        id="fiscal"
        eyebrow="Fiscal augmentation"
        title="Does the fiscal block help?"
        intro="The fiscal variant adds a block of government-finance series. It improves accuracy modestly in normal times, but the gain is small, only significant on one of four tests, and underpowered on this 34-quarter sample."
      >
        <ComparisonSection />
      </Section>

      <Section
        id="findings"
        eyebrow="Conclusions"
        title="What the evidence says"
        intro="Seven takeaways, each anchored to the numbers above (the figures are generated straight from the backtest artifacts, not typed by hand)."
      >
        <FindingsSection />
      </Section>

      <Section
        id="method"
        eyebrow="Method"
        title="How this is measured"
        intro="A pseudo-real-time backtest is only as honest as its data discipline. Here is the target, the cutoff, and the point-in-time data rules that keep it look-ahead-safe."
      >
        <MethodologyFooter />
      </Section>

      <footer className="border-t border-line bg-white py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-3 px-5 text-xs text-slate-500 sm:flex-row sm:items-center">
          <p>
            GDP Nowcast - fiscal &middot; pseudo-real-time DFM backtest, 2017 - 2025. All figures
            generated from committed point-in-time backtest artifacts.
          </p>
          <a
            href="https://github.com/mattecasta17/GDPnowcast-fiscal"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-slate-600 hover:text-ink"
          >
            github.com/mattecasta17/GDPnowcast-fiscal
          </a>
        </div>
      </footer>
    </>
  );
}
