import { AblationSection } from "@/components/AblationSection";
import { BenchmarkNotes } from "@/components/BenchmarkNotes";
import { ComparisonSection } from "@/components/ComparisonSection";
import { CumulativeImpactChart } from "@/components/CumulativeImpactChart";
import { DeficitGainBars } from "@/components/DeficitGainBars";
import { DeltaChart } from "@/components/DeltaChart";
import { FiscalNewsInfographic } from "@/components/FiscalNewsInfographic";
import { FiscalSignalSection } from "@/components/FiscalSignalSection";
import { HeadlineChart } from "@/components/HeadlineChart";
import { Hero } from "@/components/Hero";
import { MethodologyFooter } from "@/components/MethodologyFooter";
import { Nav } from "@/components/Nav";
import { Q2GainChart } from "@/components/Q2GainChart";
import { ResultsFindings } from "@/components/ResultsFindings";
import { ResultsTable } from "@/components/ResultsTable";
import { Section } from "@/components/ui";
import { VariablesSection } from "@/components/VariablesSection";
import { WeeklyExplorer } from "@/components/WeeklyExplorer";

export default function Home() {
  return (
    <>
      <Nav />
      <Hero />

      <Section
        id="variables"
        eyebrow="Model inputs"
        title="A shared macro panel plus a fiscal block"
        intro="Both models draw on the same panel of 28 macroeconomic series, grouped into eight categories. The Fiscal-enhanced specification adds a block of three fiscal series. The only difference between the two models is this fiscal block."
      >
        <VariablesSection />
      </Section>

      <Section
        id="benchmarks-results"
        eyebrow="Benchmarks & results"
        title="Forecast accuracy across periods"
      >
        <div className="space-y-6">
          <BenchmarkNotes />
          <ResultsTable />
        </div>
      </Section>

      <Section id="results-findings" title="Two takeaways">
        <ResultsFindings />
      </Section>

      <Section id="charts" title="Visual evidence">
        <div className="space-y-10">
          <div>
            <HeadlineChart />
            <p className="mt-2 text-sm text-muted">
              Both models track the BEA advance closely in normal quarters; the large misses fall on
              the genuine turning points of 2022 and 2025.
            </p>
          </div>
          <div>
            <DeltaChart />
            <p className="mt-2 text-sm text-muted">
              The fiscal block lowers the absolute error in the majority of quarters, with the
              largest gains concentrated after 2020.
            </p>
          </div>
          <div>
            <WeeklyExplorer />
            <p className="mt-2 text-sm text-muted">
              Within each quarter the nowcast is revised weekly as new data are released, converging
              toward the eventual advance.
            </p>
          </div>
        </div>
      </Section>

      <Section
        id="deficit"
        eyebrow="Core Findings"
        title="Most of the fiscal accuracy gain is the deficit's"
        intro="This section traces where the accuracy gain comes from. The fiscal block enters the model as news: the part of each release the dynamic factor model did not anticipate. The federal deficit's news is the largest of the three fiscal series; it concentrates in the second quarter and after 2020, and it tracks the growth the macro-only panel leaves unexplained. The gain over the Staff Nowcast scales with the size of this news. The deficit supplies most of the gain, though the improvement becomes statistically robust only with the full fiscal block, not the deficit alone."
      >
        <div className="space-y-6">
          <FiscalNewsInfographic />
          <FiscalSignalSection />
          <Q2GainChart />
          <CumulativeImpactChart />
          <DeficitGainBars />
          <AblationSection />
        </div>
      </Section>

      <Section
        id="fiscal"
        eyebrow="Significance"
        title="Statistical significance of the fiscal improvement"
        intro="Across both loss functions and all three periods, every Diebold-Mariano statistic favours the Fiscal-enhanced DFM: the direction of the result is consistent throughout. The improvement is significant for absolute loss over the full sample excluding 2020 (p=0.036) and not significant elsewhere. As the power analysis shows, this reflects the length of the sample rather than the absence of an effect."
      >
        <ComparisonSection />
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
