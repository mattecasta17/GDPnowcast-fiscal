# Data sources & vintage strategy (Phase 2)

How the v2 pipeline rebuilds the input data for the mixed-frequency DFM. Everything
here is produced by `gdpnowcast fetch` (`src/gdpnowcast/data/`) from **ALFRED**
(the archival/real-time companion to FRED), point-in-time, with no forward-looking bias.

## Series

Two model variants share 32 baseline macro series; the **fiscal** variant adds 3 more
(`GCEC1`, `MTSDS133FMS`, `W875RX1`). The spec lives in `Spec_US_new.xlsx` (32) and
`Spec_US_fiscal.xlsx` (35); `Model=0` rows are in the spec but deactivated in estimation.

The "earliest ALFRED vintage" column is from the pre-Phase-2 coverage spike
(`tools/alfred_coverage_spike.py`, run 2026-06-01) — all 35 reach back well before the
first backtest vintage (2016-10-03), so **no series needs a committed-vintage fallback**.

| SeriesID | Name | Freq | Transform | Model | Category | Earliest ALFRED vintage |
|---|---|:--:|:--:|:--:|---|---|
| PAYEMS | Payroll Employment | m | chg | 1 | Labor | 1955-05-06 |
| JTSJOL | Job Openings (JOLTS) | m | chg | 1 | Labor | 2010-08-11 |
| GDPC1 | Real GDP | q | pca | 1 | National Accounts | 1991-12-04 |
| CPIAUCSL | Consumer Price Index | m | pch | 1 | Prices | 1972-07-21 |
| DGORDER | Durable Goods Orders | m | pch | 1 | Manufacturing | 1999-08-04 |
| HSN1F | New Home Sales | m | pch | 0 | Housing & Construction | 1999-07-30 |
| RSAFS | Retail Sales | m | pch | 1 | Retail & Consumption | 2001-06-13 |
| UNRATE | Unemployment Rate | m | chg | 1 | Labor | 1960-03-15 |
| HOUST | Housing Starts | m | pch | 1 | Housing & Construction | 1960-07-21 |
| INDPRO | Industrial Production | m | pch | 1 | Manufacturing | 1927-01-26 |
| PPIFIS | Producer Price Index | m | pch | 0 | Prices | 2014-02-19 |
| DSPIC96 | Real Disposable Personal Income | m | pch | 1 | National Accounts | 1979-12-18 |
| BOPTEXP | Exports (BOP) | m | pch | 1 | International Trade | 2010-04-13 |
| BOPTIMP | Imports (BOP) | m | pch | 1 | International Trade | 2010-04-13 |
| WHLSLRIMSA | Wholesale Inventories | m | pch | 0 | Manufacturing | 2013-06-13 |
| TTLCONS | Construction Spending | m | pch | 1 | Housing & Construction | 2011-07-01 |
| IR | Import Price Index | m | pch | 1 | International Trade | 2010-03-16 |
| CPILFESL | Core CPI | m | pch | 1 | Prices | 1996-12-12 |
| PCEPILFE | Core PCE Price Index | m | pch | 1 | Prices | 2000-08-01 |
| PCEPI | PCE Price Index | m | pch | 1 | Prices | 2000-08-01 |
| PERMIT | Building Permits | m | chg | 1 | Housing & Construction | 1999-08-17 |
| TCU | Capacity Utilization | m | chg | 1 | Manufacturing | 1996-11-15 |
| BUSINV | Business Inventories | m | pch | 1 | International Trade | 1996-11-15 |
| ULCNFB | Unit Labor Cost | q | pca | 1 | Labor | 1968-05-27 |
| IQ | Export Price Index | m | pch | 1 | International Trade | 2010-03-16 |
| GACDISA066MSFRBNY | Empire State Mfg Index | m | lin | 1 | Surveys | 2014-03-17 |
| PCEC96 | Real Consumption Spending | m | pch | 1 | Retail & Consumption | 1979-11-19 |
| A261RX1Q020SBEA | Real Gross Domestic Income | q | pca | 0 | National Accounts | 2013-02-28 |
| GACDFSA066MSFRBPHI | Philadelphia Fed Mfg Index | m | lin | 1 | Surveys | 2015-04-16 |
| AMDMVS | Mfrs' shipments: durable goods | m | pch | 1 | Manufacturing | 2011-06-24 |
| AMDMUO | Mfrs' unfilled orders: all industries | m | pch | 1 | Manufacturing | 2011-06-24 |
| AMDMTI | Mfrs' inventories: durable goods | m | pch | 1 | Manufacturing | 2011-06-24 |
| GCEC1 | Real Govt Consumption & Investment | q | pca | 1 | **Fiscal** | 1958-12-21 |
| MTSDS133FMS | Federal Surplus/Deficit [-] | m | lin † | 1 | **Fiscal** | 2015-09-11 |
| W875RX1 | Real personal income ex. transfers | m | pch | 1 | **Fiscal** | 2010-05-28 |

† `MTSDS133FMS` is `lin` in the spec but is **re-specified to `ch1` (12-month difference) in
Phase 4** — loading it as raw levels imports strong April seasonality that inflates the "Q2
fiscal effect" (audit verification: April = +1.13σ on `lin`, 0.12σ on `ch1`). The two survey
indices (`GACDISA…`, `GACDFSA…`) are `lin` by design (already stationary diffusion indices).

## Vintage strategy

- **Manifest-driven.** `gdpnowcast fetch` iterates a committed manifest of vintage dates
  (`configs/vintages_baseline.csv`, `configs/vintages_fiscal.csv`), generated from the real v1
  vintage filenames by `tools/make_vintage_manifest.py`. **486 vintages each**, range
  **2016-10-03 → 2025-07-25**.
- **Includes the quarter-start re-estimation vintages.** 452 are Fridays; **34 are
  quarter-start business days** (Jan/Apr/Jul/Oct 1-3) on which the DFM re-estimates parameters.
  A Fridays-only rule (v1's `fridays_between`) silently drops these — the DFM then cannot
  reproduce `Results.pdf`. The manifest keeps them, and `tests/test_vintages.py` asserts none
  are dropped.
- **Output format** matches v1's `Functions/load_data.py::readData`: one Excel file per vintage
  (`YYYY-MM-DD.xlsx`) with a monthly `Date` column (`freq="MS"`, 1985-01 → vintage month) plus
  one column per `SeriesID`. Baseline → `data/US_new/`, fiscal → `data/US_fiscal/` (both
  gitignored; rebuilt on demand).

## Point-in-time / no-leakage policy

The entire backtest's validity rests on each vintage as-of date `D` containing **only what was
known at `D`** (Matteo's standing forward-looking-bias guardrail).

- Each series is fetched once via `get_series_all_releases` (full ALFRED release history,
  `[realtime_start, date, value]`). For a vintage `D`, the as-of value of each observation is
  the latest value whose `realtime_start <= D` (`reconstruct_asof` in `data/fred.py`).
- **No ffill, no interpolation, no backfill.** A cell with no as-of value stays NaN.
- Observations are truncated to `date <= D` (you cannot observe the future).
- **Verified:** `tests/test_fetch_integration.py` cross-validates `reconstruct_asof` against the
  authoritative point-in-time API (`get_series(realtime_start=D, realtime_end=D)`) for sampled
  (series, vintage) pairs — values match exactly (`rtol=0, atol=0`) — and asserts no observation
  is dated after the vintage.

## Quarterly convention

FRED returns quarterly series stamped at quarter-start (e.g. Q1 → Jan-01). v1 lands them on the
**last month of the quarter** (Mar/Jun/Sep/Dec) via a `+2`-month shift, because the loader reads
quarterly rows at indices 2/5/8/… (`load_data.py:144`). `asof_series(..., frequency="q")` applies
this shift for the 4 quarterly series: `GDPC1`, `ULCNFB`, `A261RX1Q020SBEA`, `GCEC1`. Removing
the shift would silently NaN-out the series, not just misalign it.

## Known v1 quirks (documented, not hidden)

- **`2021-01-04` fiscal gap (now completed).** v1's `data/US_fiscal/` had 485 files — it was
  missing the `2021-01-04` quarter-start vintage that the baseline set had. v2 completes the
  fiscal manifest to 486 (Decision D2). Consequence for Phase 3a/4: the fiscal backtest now has
  one re-estimation vintage that v1's `Results.pdf` did not — flag this when comparing to v1.
- **Baseline-series provenance — verified to reproduce v1 exactly.** v1 had **no fetcher** for the
  32 baseline series (`variables_creation.py` only patched the 3 fiscal ones); their v1 vintage
  files came from a different source (FRBNY pipeline), so we expected the v2 ALFRED fetcher might
  not match. **It does — exactly.** The full Task 9 fetch (2026-06-01) reproduces every v1 file:
  `tools/compare_to_v1.py` over **all** vintages found **0 difference across 11.3M cells**
  (baseline 5,428,161 + fiscal 5,906,348; global max abs delta = 0, no diverging series). The
  FRBNY-pipeline baseline values were themselves ALFRED point-in-time data, and the v2
  reconstruction recovers them bit-for-bit. The **Phase 2 exit gate is the filename superset**
  (`tests/test_superset.py`, PASSED for both variants); the value match is the diagnostic
  (Decision D3 — reported, not gated).
- **4 vintages carry one extra trailing all-NaN month vs v1 (cosmetic).** `2016-10-03`,
  `2016-12-02`, `2016-12-07`, `2017-02-03` (both variants): v2's monthly index runs through the
  vintage's own month, which at those early-in-the-month as-of dates has **no** published data yet
  (the whole row is NaN), so v1 trimmed that empty trailing month. No observed value differs, and
  it is the vintage's own month (not the future) so it is not look-ahead; the DFM treats an
  all-NaN trailing month as no information. `data/US_*_v1/` is a strict subset of the v2 rows here
  (`only_in_v1` is empty in every case).
- **FRED API key** was committed in plaintext in v1 (`variables_creation.py:25`), now rotated;
  `.env` is the single source of truth (`load_dotenv(override=True)` so a stale OS env var can't
  shadow it).
- **`DSPIC96` / `W875RX1` SeriesName labels.** `DSPIC96` is *Real Disposable* Personal Income on
  FRED (spec says "Personal Income"); `W875RX1` is market income *ex transfers*. Both left as-is
  pending a paper-reviewer flag (design-doc §8 open-q #5).
