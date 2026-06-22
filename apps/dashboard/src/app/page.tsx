import { BenchmarkSection } from "@/components/BenchmarkSection";
import { ComparisonSection } from "@/components/ComparisonSection";
import { FindingsSection } from "@/components/FindingsSection";
import { FiscalSignalSection } from "@/components/FiscalSignalSection";
import { HeadlineChart } from "@/components/HeadlineChart";
import { Hero } from "@/components/Hero";
import { KpiStrip } from "@/components/KpiStrip";
import { MethodologyFooter } from "@/components/MethodologyFooter";
import { Nav } from "@/components/Nav";
import { QuarterErrorChart } from "@/components/QuarterErrorChart";
import { TraditionalModelsSection } from "@/components/TraditionalModelsSection";
import { Section } from "@/components/ui";
import { WeeklyExplorer } from "@/components/WeeklyExplorer";

export default function Home() {
  return (
    <>
      <Nav />
      <Hero />
      <KpiStrip />

      <Section
        id="fiscal"
        eyebrow="The headline question"
        title="Fiscal-enhanced DFM vs Staff Nowcast"
        intro="The thesis, head-to-head: does adding a fiscal block to a macro dynamic factor model improve the nowcast? On aggregate the Fiscal-enhanced DFM edges the macro-only Staff Nowcast and wins a majority of quarters - a modest, consistent gain, not yet significant at conventional thresholds on this short sample."
      >
        <ComparisonSection />
      </Section>

      <Section
        id="deficit"
        eyebrow="Why it works"
        title="The fiscal signal: deficit surprises"
        intro="Where does the edge come from? Almost entirely the federal deficit, and almost entirely after 2020. The fiscal block's news (realized minus forecast, weighted) is several times larger post-COVID, and in the quarters where it is largest the Fiscal-enhanced DFM gains the most accuracy over the Staff Nowcast."
      >
        <FiscalSignalSection />
      </Section>

      <Section
        id="headline"
        eyebrow="Accuracy"
        title="Nowcast vs the BEA advance"
        intro="One point per quarter: each model's pre-advance forecast against the number the BEA actually printed first. Both variants track the advance closely in calm quarters and miss the genuine real-economy surprises (2022, 2025q1)."
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
        eyebrow="Vs tradition"
        title="DFM family vs traditional models"
        intro="Step back from fiscal-vs-macro: how does the dynamic factor approach compare to traditional univariate models fit to past GDP growth alone? In normal times it is mid-pack on point accuracy - no free lunch. Across the full sample including 2020, it is far more robust."
      >
        <BenchmarkSection />
      </Section>

      <Section
        id="traditional"
        eyebrow="The contestants"
        title="What the traditional models are"
        intro="The four benchmarks the DFMs are measured against - what each one is, why it is a fair test, and why the Atlanta Fed's GDPNow is deliberately not in the table."
      >
        <TraditionalModelsSection />
      </Section>

      <Section
        id="findings"
        eyebrow="Conclusions"
        title="What the evidence says"
        intro="Eight takeaways, fiscal-first, each anchored to the numbers above (the figures are generated straight from the backtest artifacts, not typed by hand)."
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
