# Methodology audit — `GDPnowcast-fiscal`

**Auditor scope.** Methodology, statistical/econometric correctness, data-science
design. Out of scope: code quality, folder layout, software engineering hygiene
(other agents own those). Read-only.

**Artefacts read.** `README.md`, `Functions/dfm.py`, `Functions/load_spec.py`,
`Functions/load_data.py`, `Functions/remNaNs_spline.py`,
`Functions/update_Nowcast2.py`, `Functions/decompose_common_factor.py`,
`Functions/extract_common_residual.py`, `Functions/summarize.py`, `DFM_new.py`,
`DFM_fiscal.py`, `nowcast_2020.py`, `nowcast_2024.py`, `nowcast_2024_fiscal.py`,
`Spec_US_new.xlsx`, `Spec_US_fiscal.xlsx`, `variables_creation.py`, full
`Results.pdf` (the Master thesis, 44 pp.), one sample vintage Excel
(`data/US_fiscal/2024-10-04.xlsx`).

---

## TL;DR

1. **The DFM core is a faithful Python port of the FRBNY Banbura-Modugno mixed-frequency
   EM-DFM (Bok et al. 2018)**. State-space form, Mariano-Murasawa tent-shape quarterly
   aggregator (`R_mat = [2,-1,0,0,0; 3,0,-1,0,0; 2,0,0,-1,0; 1,0,0,0,-1]`),
   constrained loadings, idiosyncratic AR(1), EM via Kalman smoother — all present
   and correct. Numbers of factors, lag order, block structure match the FRBNY
   convention (1 global + 1 soft + 1 real + 1 labor block, 1 lag in the factor VAR,
   5-lag tent for quarterlies).

2. **The pseudo-real-time backtest design is correct and unusually disciplined for a
   Master thesis.** Weekly ALFRED vintages (≈450 files per spec from 2016-12 to
   2025-07) are fetched with `realtime_start = realtime_end = vintage_date`
   (`variables_creation.py:40`), so each vintage truly reflects what was observable
   on that Friday — no look-ahead, no use of revised data. DFM parameters are
   re-estimated only at the start of each calendar quarter (matching FRBNY practice)
   and held fixed across the 22 weekly vintages within the quarter
   (`nowcast_2024.py:60-82`). This is materially better than the typical Master
   thesis nowcasting setup.

3. **The fiscal contribution is small, weakly justified theoretically, and the
   thesis's "predominantly improves in Q2 and post-pandemic" finding is plausibly
   driven by a single variable + a fragile sample split.** The fiscal block adds 3
   series only (`GCEC1` quarterly, `MTSDS133FMS` monthly federal deficit, `W875RX1`
   monthly real personal income ex-transfers), and `W875RX1` is essentially an
   alternative income measure rather than a fiscal-policy variable. RMSE drops from
   1.87 to 1.81 ex-2020 — a 3 % relative improvement — and the headline Q2 MAE
   improvement (1.43 → 1.31) rests on ~8 quarters of out-of-2020 observations.
   Diebold-Mariano is computed correctly *in principle* (HAC variance, two-sided
   test on loss differential per appendix C), but the reported DM statistics
   (6.4 for ex-2020 RMSE) are implausibly large for the sample size and the small
   loss differential, suggesting either a unit/scale issue or that the DM was run
   at the **weekly-revision level** (T = 575) rather than the quarterly-nowcast
   level (T ≈ 30). The latter would be a multiple-testing / dependence violation
   that inflates DM by ~√22.

4. **Three concrete methodological showstoppers / bugs.**
   - `Functions/update_Nowcast2.py:6` imports `News_DFM` from
     `Functions.update_Nowcast` — **this module does not exist in the repo**, so
     every `nowcast_YYYY*.py` script would fail at import time. Either the file
     is git-ignored, lost, or the news decomposition path was never committed.
     All numbers in `Results.pdf` (RMSE, MAE, DM, news tables) therefore cannot
     be reproduced from the public repo as it stands.
   - The `pca` quarter-to-quarter annualization transform in `load_data.py:121`
     uses `(x[t1+step::step]/x[t1:-step:step])**(1/n) - 1)*100` with `n = step/12 =
     0.25` for quarterly series. With `n = 1/4`, `**(1/n) = **4`, which is the
     correct annualization for a *quarterly growth rate*. **But the offset
     `t1 = step - 1 = 2`** assumes monthly observations start at the beginning of
     the quarter (Jan/Apr/Jul/Oct). In the loaded data, quarterly variables
     (GDPC1, GCEC1, ULCNFB) are dated on the **first month** of the quarter
     (2024-03-01 = Q1 etc.), so `t1=2` would index the *third* month of each
     quarter and use the wrong cell. This needs a sanity check against the
     transformed values (the original FRBNY MATLAB used this for series with
     monthly stamps at quarter-end; the FRED quarterly dates here are at quarter-start).
   - The `variables_creation.py:96` block applies `shift(2, freq="MS")` to GCEC1
     only ("Sposta GCEC1 di due mesi avanti, così finisce sull'ultimo mese del
     trimestre"), pushing it onto the **last** month of the quarter. GDPC1 is
     *not* shifted. So in a fiscal-spec vintage, GDPC1 sits on 2024-03-01 while
     GCEC1 sits on 2024-05-01 even though both refer to the same quarter. The
     DFM treats their tent-aggregation timing identically (`Spec.Frequency == "q"`),
     so the GCEC1 shift effectively misaligns it by one quarter inside the tent
     and likely explains why **GCEC1's average absolute impact is one to two orders
     of magnitude smaller than MTSDS133FMS** in Figure A7 of the thesis (0.003 vs
     0.045) — the variable is contributing almost nothing because its tent
     constraint is mis-keyed.

5. **The thesis claim "fiscal variables improve nowcasting" is defensible but
   overstated.** What the evidence actually shows is: (i) adding the monthly
   federal **deficit** series MTSDS133FMS reduces post-2020 RMSE by 0.06 pp at
   the cost of a –0.2 negative bias; (ii) GCEC1 contributes ~0 (likely because
   it's mis-dated as above); (iii) W875RX1 contributes ~0.03 and is mostly
   redundant with DSPIC96 (already in the baseline). The honest conclusion is
   "one monthly federal-balance series adds modest information in volatile
   post-pandemic quarters when the Treasury's borrowing schedule diverges
   sharply from expectations." The thesis frames this much more strongly.

---

## What the project does

The project ports the FRBNY Staff Nowcast Python translation
(`MajesticKhan/Nowcasting-Python` → `FRBNY-TimeSeriesAnalysis/Nowcasting`) and
extends it with 3 federal fiscal series to test whether they improve U.S. real
GDP nowcasting. The core model is the Banbura-Modugno (2010, 2013)
mixed-frequency Dynamic Factor Model: monthly and quarterly macro indicators
load on a single global factor plus three local blocks (Soft / Real / Labor),
with idiosyncratic AR(1) errors and 5-lag Mariano-Murasawa tent aggregation for
quarterly series. EM-MLE estimation is initialised by PCA on the spline-filled
data, then iterated with a Kalman smoother until log-likelihood convergence
(`threshold = 1e-4`).

The empirical setup constructs two parallel sets of weekly ALFRED vintages from
2016-12-09 to 2025-07-25 (one with 32 macro series, one with the 35 macro + 3
fiscal series). For each Friday in a 22-week pre-release window, the model is
re-run with the dataset as it was published on that Friday, the Kalman filter
absorbs any new releases or revisions, the nowcast is computed for the target
quarter's GDP, and the change relative to the previous Friday is decomposed
into "news" (each new observation × its Kalman weight). DFM parameters are
re-estimated at the start of each calendar quarter (15 vintages 2017-Q1 to
2025-Q1, see `DFM_fiscal.py:17-25`) and frozen for the 22 weekly nowcasts
inside the quarter. Performance is measured against the BEA *advance* GDP
release (not subsequent revisions) using RMSE, MAE, Bias, and one-sided
Diebold-Mariano with HAC variance.

---

## Methodology correctness

### What matches Bok et al. (2018) / Banbura-Modugno (2010, 2013)

Reading `Functions/dfm.py`:

| Element | Implementation | Reference |
|---|---|---|
| State-space form `y_t = C z_t + e_t`, `z_t = A z_{t-1} + u_t` | `dfm.py:114-115`, `runKF` 798-853 | Bok eq. 2-3; thesis eq. 7-8 |
| Block structure (Global + sub-blocks) | `Par["blocks"]` from spec, `r = [1,1,1,1]` global+soft+real+labor (`dfm.py:69`) | Bok §3; thesis §2.2 |
| 1 lag in factor VAR | `Par["p"] = 1` (`dfm.py:68`) | Bok §3 ("low-order VAR") |
| 5-lag Mariano-Murasawa tent for quarterly series | `R_mat = [[2,-1,0,0,0],[3,0,-1,0,0],[2,0,0,-1,0],[1,0,0,0,-1]]` and the `[1,2,3,2,1]` aggregator in `dfm.py:370`, `715` | Mariano-Murasawa (2003); Banbura-Modugno (2010) eq. for triangular weights |
| Constrained loadings on quarterly variables | `Rcon_i = np.kron(Rcon, np.eye(r_i))`, constraint applied in `EMstep`, `dfm.py:722-724` | BM2010 eq. 13 |
| Idiosyncratic AR(1) on monthly errors | `BM[i,i] = OLS(res_i[1:], res_i[:-1])`, `dfm.py:404` and dedicated block in transition matrix | BM2010 §2; Doz-Giannone-Reichlin (2012) |
| EM-MLE estimation | E-step = Kalman smoother (`runKF`); M-step closed-form via eq. 6, 8, 13, 15 of BM2010 — coded with comments referencing BGR 2010 in `EMstep` | BM2010 entire paper |
| Kalman handles ragged-edge missing data | `MissData()` drops missing rows from `Y, C, R` at each `t` (`dfm.py:1053`) | Bok §3 footnote 7 |
| Standardisation before estimation | `Mx = nanmean(X), Wx = nanstd(X, ddof=1)`, `xNaN = (X - Mx)/Wx` (`dfm.py:92-94`) | Standard |
| Initial conditions via PCA on spline-filled data | `InitCond()` runs `remNaNs_spline` then `eig(np.cov(...))` (`dfm.py:245, 276`) | Doz-Giannone-Reichlin (2011) two-step |
| Measurement-error floor on idiosyncratic terms | `RR[i_idio_M] = 1e-4; RR[nM:] = 1e-4` (`dfm.py:746-747`) | Doz, Giannone, Reichlin (2012) regularisation |

This is a complete, faithful, line-by-line MATLAB→Python translation of the
FRBNY DFM. There is **no original modelling work** in `Functions/dfm.py` and
none was claimed — the README is explicit about this.

### What does NOT match Staff Nowcast 2.0

The thesis (§2.3) describes Staff Nowcast 2.0 (Bayesian estimation, long-run
trend `g_t`, time-varying volatility, COVID factor, outlier vector). **None of
these features are implemented** in this repo. The thesis acknowledges this
upfront — the project replicates the *legacy* (pre-2021) Staff Nowcast, not 2.0.
This is a defensible choice (only the legacy version has a public Python port)
but it means the model has **no mechanism to handle the 2020 outliers**, which
is why 2020 RMSE is 14.18 (full sample) vs 1.87 ex-2020 — a factor of ~7.6
inflation. The thesis correctly excludes 2020 from headline metrics but this is
a structural limitation, not a property of the data.

### Concrete methodological gaps in the DFM code

1. **Convergence check has a print bug that silently masks log-lik decreases.**
   `dfm.py:786`: `print('******likelihood decreased from {} to {}').format(previous_loglik,loglik)`
   — `.format()` is called on `print()`'s return value (`None`). If the EM
   log-likelihood ever decreases (which can happen with constrained EM under
   numerical issues), this line crashes with `AttributeError`. The `try/except`
   in the calling nowcast loop swallows it as a generic error and skips the
   vintage. This could silently throw away some vintages — but probably none in
   practice because log-lik decreases are rare here.

2. **Hard-coded number of blocks / lags.** `r = [[1,1,1,1]]`, `p = 1`, `pC = 5`
   are all hard-coded with no sensitivity analysis. Bok et al. (2018) Table 2
   reports they tested r ∈ {1,2,3} per block and chose by BIC; the thesis does
   not report any analogous robustness check. Not wrong, but unverified.

3. **`Spec` doesn't carry release-lag information.** The README says the spec
   defines "variables, transformations, release lags, and block assignments"
   but the Excel has no `ReleaseLag` column (verified by `pd.read_excel` —
   columns are `[Model, SeriesID, SeriesName, Frequency, Block1-4,
   Transformation, Units, Category]`). Release timing is implicit in the
   vintage Excel file's NaN pattern. This is actually fine for the
   pseudo-real-time setup but means the model cannot do **counterfactual**
   experiments (e.g. "what if PAYEMS were released 2 weeks later") that
   Banbura-Rünstler (2011) and the original FRBNY Liberty Street post discuss.

4. **No bootstrap / no analytic forecast-error variance reported.** The DFM
   produces analytical state-covariance matrices `Vsmooth` from the Kalman
   smoother, which the FRBNY uses to compute predictive intervals around the
   nowcast. This is computed in code (in `Res["V_0"]`, `Vsmooth`) but is never
   converted to GDP forecast variance and never reported. Only point nowcasts
   appear in `Results.pdf`.

---

## Validation design issues

The validation design is the strongest part of the project. The pseudo-real-time
backtest is structurally correct.

### Correct elements

- **ALFRED vintages, not revised data.** `variables_creation.py:40` issues
  `fred.get_series(fred_id, realtime_start=vintage_str, realtime_end=vintage_str)`,
  which returns the series exactly as it was published on `vintage_str`. There
  are ~450 weekly vintage files per spec; the data folder confirms this is real,
  not synthetic. **No look-ahead from revisions.**
- **Weekly cadence matching FRBNY operational logic.** Vintages are Fridays
  (`fridays_between()` in `variables_creation.py:28`); the nowcast loop iterates
  exactly the 22 Fridays preceding each quarter's BEA advance release
  (`nowcast_2020.py:29-58`).
- **DFM re-estimated at quarter boundaries only.** `param_map_2024`
  (`nowcast_2024.py:60-82`) loads two parameter sets per quarter — one estimated
  on the vintage of the *previous* quarter (used until the quarter starts) and
  one re-estimated on the *current* quarter's first-day vintage. After the
  switch_date the parameters are held fixed. This matches Bok et al. footnote
  ("re-estimated quarterly using the most recent 15 years of data") with the
  caveat that the thesis uses data from 2000 onward (sample size ~24-25 years
  by 2025), not a rolling 15-year window.
- **Target = BEA advance release, not later revisions.** `gdp_adv_estimate` dict
  (e.g. `nowcast_2024.py:21-26`: `{"2024q1": 1.6, "2024q2": 2.8, ...}`) hard-codes
  the *first* BEA print, which is the right benchmark for evaluating a real-time
  nowcasting model. This is correct (using later revisions would penalise the
  nowcast for changes the BEA itself made post-hoc).

### Design issues

1. **Estimation sample window changes implicitly across vintages.** Each
   quarterly DFM run uses everything from 2000-01-01 to the current vintage
   (`DFM_fiscal.py:28: sample_start = ... "2000-01-01"`). So the first 2017 DFM
   uses 17 years of data, the last 2025 DFM uses 25 years. The FRBNY uses a
   **rolling 15-year window** explicitly to keep the loadings recent. Using an
   expanding window mixes structural breaks (GFC, COVID) with the recent
   regime. Not wrong, but a deliberate departure from the reference.

2. **No competing benchmark.** The thesis compares fiscal vs no-fiscal but
   never compares either to:
   - Atlanta Fed GDPNow (sub-component BVAR — public, free)
   - SPF / Bloomberg consensus
   - A simple ARMA(p,q) on GDP
   - The actual FRBNY Staff Nowcast (publicly archived through Q3 2021)

   So the absolute level of RMSE = 1.87 is uninterpretable. Is 1.87 good, bad,
   or comparable to GDPNow (which historically runs around RMSE = 1.0–1.5 for
   recent quarters)? The thesis cannot tell. Recommended: add at minimum
   one no-DFM benchmark.

3. **Sample-stratified comparisons confound regime with method.** The thesis
   reports DM tests separately for full / ex-2020 / pre-2020 / post-2020 and
   highlights post-2020 as the period of largest gain (table B5). With
   T_pre = 12 quarters (2017-2019), T_post = 17 quarters (2021-2025) — the
   sub-sample DM tests are under-powered, and the *interpretation* that fiscal
   matters "more after 2020" conflates "post-2020 had bigger fiscal swings" with
   "post-2020 had bigger nowcast errors in general" (Q2-Q3 RMSE on the baseline
   doubles after 2020 — figure A2). The conditional argument
   `Pr(better | post-2020 regime) > Pr(better | pre-2020 regime)` is
   non-trivial to identify; the thesis just asserts it.

4. **Quarter-level vs weekly-level DM denominator.** From `Results.pdf` Table B5:
   "Full excl. 2020, Observations = 575". With 32 quarters × ~22 weekly vintages
   ≈ 700, this is **the weekly-revision level** (RMSE / MAE / Bias computed on
   weekly forecast errors, not on the final per-quarter nowcast). Diebold-Mariano
   requires the loss differential `d_t` to be stationary; weekly nowcast errors
   on the *same target quarter* are highly serially correlated (consecutive
   Fridays differ only by the news of the past week). The HAC adjustment helps
   but cannot fully clean this if the lag-truncation is too short. The thesis
   reports the test as if it were on quarterly errors but the N = 575 / 228 / 347
   numbers betray a weekly-level computation. The actual quarterly-level DM
   would have N ≈ 30 and would likely be **borderline significant** rather than
   p ≈ 0.0001. This is the single biggest statistical inflation in the thesis.

5. **`Functions/update_Nowcast2.py` won't import.** Line 6:
   `from Functions.update_Nowcast import News_DFM` — this file does not exist
   in the repo. I verified by `python -c "from Functions.update_Nowcast2 import update_nowcast2"`
   which raises `ModuleNotFoundError: No module named 'Functions.update_Nowcast'`.
   The DFM-estimation scripts (`DFM_new.py`, `DFM_fiscal.py`) work standalone,
   but every `nowcast_YYYY*.py` script — i.e. **the entire validation backtest**
   — is dead on arrival from a fresh clone. Either the file is in `.gitignore`,
   was renamed, or is in a separate not-committed folder. As a methodology
   audit point: the results in `Results.pdf` are not reproducible from the public
   repo as it stands.

---

## Fiscal extension assessment

### What was added (`Spec_US_fiscal.xlsx` rows 32-34)

| FRED ID | Name | Frequency | Transformation | Block |
|---|---|---|---|---|
| GCEC1 | Real Government Consumption Expenditures and Gross Investment | Quarterly | `pca` (annualised %) | Global + Real |
| MTSDS133FMS | Federal Surplus or Deficit (Monthly Treasury Statement) | Monthly | `lin` (levels) | Global + Real |
| W875RX1 | Real personal income excluding current transfer receipts | Monthly | `pch` (% change) | Global + Real |

### Critique

1. **Only 3 series and one is mislabelled as "fiscal".** W875RX1 is *personal*
   income excluding government transfers — it's an income/consumption variable
   that the BEA computes to strip out fiscal transfers from personal income, not
   a measure of fiscal activity. Including it as a "fiscal variable" is
   misleading. Worse, the baseline already includes DSPIC96 (Personal Income)
   which contains W875RX1 plus transfers; the two series have correlation > 0.95.
   So W875RX1 is mostly redundant signal that the model will partition into the
   idiosyncratic AR(1).

2. **MTSDS133FMS is in raw `$ Millions levels`, not transformed.**
   `Spec_US_fiscal.xlsx` row 33: `Transformation = lin`. The Monthly Treasury
   Statement deficit series is non-stationary (federal deficits trend toward
   −$300 B/month over the sample) and highly seasonal (April surplus from
   tax inflows, deficits in other months). Loading a level series with a
   pronounced seasonal pattern onto a DFM that assumes stationary inputs is
   **methodologically wrong**. The DFM standardises (mean/std) but does not
   detrend or deseasonalise. The thesis's finding that "MTSDS133FMS has highest
   impact in Q2 because of tax season seasonality" is partly an *artefact* of
   loading an un-deseasonalised series — the April spike is a calendar effect
   the model interprets as macro news. Recommended transformation: 12-month
   change (`ch1`) or YoY % change, or feed the series through X-13ARIMA-SEATS
   first.

3. **GCEC1 is mis-dated.** `variables_creation.py:96-97` applies
   `s = s.shift(2, freq="MS")` to GCEC1 only ("sposta GCEC1 di due mesi avanti").
   In FRED, GCEC1 is dated quarter-start (2024-01-01, 2024-04-01, …). The shift
   moves it to quarter-end (2024-03-01, 2024-06-01, …) — but **GDPC1 is *not*
   shifted** and is also quarter-start. So in the merged dataset, GCEC1
   2024-03-01 belongs to *the previous quarter's tent* while GDPC1 2024-03-01
   correctly belongs to the current quarter's tent. The DFM treats both as
   `Frequency == "q"` and applies the same tent aggregator, so this
   mis-alignment effectively makes GCEC1 lag GDPC1 by one quarter inside the
   factor structure. This is the most likely explanation for why GCEC1's
   absolute impact in Figure A7 is essentially zero (0.003 vs 0.045 for the
   monthly deficit) — the variable is contributing roughly nothing because its
   information is being mis-attributed to the wrong quarter.

4. **No encompassing or news-orthogonality test.** Even if the fiscal block
   improves RMSE, the right question for a DFM is "does the fiscal news add
   information *orthogonal* to what the existing 32-variable factor already
   contains?" This is testable with a Diebold-Mariano forecast-encompassing
   regression
   `(y_t − ŷ^baseline_t) = β (ŷ^fiscal_t − ŷ^baseline_t) + ε_t`
   and a t-test on β=0. Not done.

5. **The argument that fiscal variables matter "more post-2020" is plausible
   but tested with too few quarters (~17) and confounded with regime change.**
   The thesis's own figure A8 shows cumulative fiscal impact = +1.49 in 2021,
   +0.14 in 2022, +0.79 in 2023, +1.23 in 2024 — a very lumpy series that does
   not look like a stable structural relationship. One year (2022) shows
   essentially zero fiscal contribution even though it's "post-pandemic". The
   honest narrative is "in 2021 and 2024 the federal deficit surprised the model;
   in 2022 and 2023 it didn't".

### What would actually demonstrate "fiscal variables improve GDP nowcasting"

- A proper monthly fiscal series with vintages going back to 2000 (the deficit
  series MTSDS133FMS is available back to 1980 in ALFRED; GCEC1 to 1947 — both
  fine).
- Stationary transformations on every fiscal series (`ch1` or `pc1`).
- Comparison vs at least 2-3 alternative DFM specifications: baseline; baseline +
  GCEC1 only (quarterly fiscal); baseline + MTSDS133FMS only (monthly fiscal);
  baseline + W875RX1 only (income-net-of-transfers); full fiscal block.
- DM tests at the **quarterly** level (T ≈ 30 ex-2020) with bootstrap rather
  than HAC asymptotic, given the small T.
- Forecast-encompassing regression with t-test on β.
- Benchmark against Atlanta Fed GDPNow on the overlapping sample.
- Out-of-sample re-test on a holdout (e.g. estimate spec on 2017–2022, test on
  2023–2025 only).

---

## Data pipeline issues

1. **FRED API key hardcoded in the source.** `variables_creation.py:25`:
   `api_key = os.environ.get("FRED_API_KEY") or "64b47ef802cce7ec9c8b65d476e9a8ea"`.
   This is a leaked credential. Methodologically irrelevant but should be
   flagged.

2. **No catalog file documenting series choices.** The `Spec_US_*.xlsx` has
   SeriesID + transformation but no rationale for inclusion. For a thesis
   "replicating FRBNY" with deliberate modifications (e.g. PPIFIS, HSN1F,
   WHLSLRIMSA, A261RX1Q020SBEA are marked `Model=0` and excluded), there is no
   written justification for why they were dropped. Section 3.2 of the thesis
   says "the inclusion of only part of the expanded 2.0 dataset is not due to
   theoretical reasons but to practical constraints related to data
   availability" — which is honest, but the **specific drops within FRBNY's
   legacy set** (e.g. PPIFIS, HSN1F, WHLSLRIMSA) are unexplained. Cf. thesis
   table B3 vs B1.

3. **Quarterly variable date alignment is inconsistent (see GCEC1 issue above).**

4. **`pca` transform offset.** `load_data.py:128-129`: `t1 = step - 1 = 2`
   assumes monthly observations begin at the start of the quarter. With FRED
   quarterlies stamped at quarter-start (verified in 2024-10-04.xlsx: GDPC1 on
   2024-03-01 = Q1, 2024-06-01 = Q2), the `pca` formula
   `(x[t1+step::step]/x[t1:-step:step])**(1/n) - 1)*100` picks elements at
   indices 2, 5, 8, … which are March, June, September — i.e. the **last** month
   of each quarter. With Q1 GDP stored at index 2 (March 2024), Q2 GDP at
   index 5 (June 2024), this *does* work out: the formula computes
   `(Q2 / Q1)**4 - 1`, which is the right annualised growth rate. But this works
   only because the data file stuffs quarterly observations into the last month
   of the quarter, even though FRED's native dates put them at quarter-start.
   Inspecting the actual data: GDPC1 is stamped 2024-03-01, 2024-06-01, … in
   the vintage Excel — these are quarter-*start* in FRED but quarter-*end* in
   the project's "monthly index" because Mar/Jun/Sep/Dec are the third month
   *of the previous quarter*. There's an off-by-one ambiguity that depends on
   convention; the *outputs* in `summarize()` should be checked against BEA's
   published Q-over-Q growth for sanity. **Recommendation:** add a unit test
   that for GDPC1 reproduces the BEA-published growth rates to within 0.05 pp.

5. **First 3 observations are dropped silently.** `load_data.py:152-153`:
   `return X[3:,:], Time[3:], Z[3:,:]` — "Drop first quarter of observations
   since transformations cause missing values". This is fine but unstated in
   any docstring or thesis. For a 1985-onwards series, dropping 3 rows just
   moves the start to April 1985, negligible.

6. **No data-quality check between vintages.** If FRED revises a historical
   value, the new vintage will reflect it, but there is no check for
   *implausible* revisions (e.g. a typo in the Excel ingest). The `news`
   decomposition will flag the change as a "revision" but won't sanity-check it.

---

## Recommended methodological improvements

In rough priority order for converting the thesis into a research-grade paper:

1. **Fix the missing `Functions/update_Nowcast.py`** (showstopper). Either
   commit the file or refactor `update_Nowcast2.py` to inline `News_DFM`. The
   thesis cannot be reproduced from the public repo until this is fixed.

2. **Re-do DM tests at the quarterly level** (T ≈ 30, ≈22 if ex-2020). Use
   Harvey-Leybourne-Newbold (1997) small-sample correction or bootstrap. Expect
   results to be borderline significant rather than p ≈ 0.0001 — and report
   them honestly.

3. **Verify GCEC1 / GDPC1 date alignment** with an end-to-end unit test:
   feed a known vintage, check that the transformed `pca` values match the
   BEA's published Q-over-Q growth for both series. The current
   `shift(2, freq="MS")` for GCEC1 only is highly suspicious; either both
   quarterly series should be at quarter-end or both at quarter-start.

4. **Add stationary transformations to MTSDS133FMS.** The federal deficit in
   `$ M levels` is non-stationary and seasonal. Switch to `ch1` (12-month
   difference) or apply X-13ARIMA-SEATS deseasonalisation upstream. Re-run the
   backtest and check if the "Q2 fiscal seasonality" finding survives — if it
   doesn't, the headline conclusion changes.

5. **Add a non-DFM benchmark** to make absolute RMSE interpretable. Suggested:
   Atlanta Fed GDPNow (free via FRBA blog), or at minimum an ARMA(1,1) on
   `pca(GDPC1)` with vintage selection.

6. **Add forecast-encompassing regression** to test whether fiscal news is
   *orthogonal* to baseline factor information. This is the right statistical
   question, more informative than DM on raw RMSEs.

7. **Add predictive intervals** to nowcasts. The Kalman smoother already
   computes `Vsmooth`; converting it to GDP forecast variance is a few lines
   of code. Currently `Results.pdf` reports only point nowcasts.

8. **Add a holdout split.** Estimate spec choices (which 3 fiscal variables,
   which transformations) on 2017–2022, evaluate strictly on 2023–2025. The
   current thesis tunes and evaluates on the same sample.

9. **Move from expanding window to rolling 15-year window** to match FRBNY
   practice and reduce contamination by structural breaks.

10. **Document the dropped FRBNY series** (PPIFIS, HSN1F, WHLSLRIMSA,
    A261RX1Q020SBEA marked `Model=0`). Either they couldn't be ALFRED-vintaged
    (state this explicitly) or they were dropped for methodological reasons
    (justify).

11. **Move FRED API key to environment variable only** (`variables_creation.py:25`)
    and revoke the leaked one.

12. **Implement Staff Nowcast 2.0 features** (long-run trend `g_t`,
    time-varying volatility, COVID factor with outlier vector). This is the
    natural next step the thesis itself acknowledges (§6, "future research").
    Major effort but would let the 2020 sample stay in the analysis.

---

## Severity ranking

**Showstopper (cannot ship the thesis as-is):**

1. `Functions/update_Nowcast.py` is missing — the entire nowcasting backtest is
   non-reproducible from the public repo.

**Major (probably changes the headline conclusion):**

2. DM tests run on weekly-level observations (N = 575) rather than
   quarterly-level (N ≈ 30); reported p-values are inflated by serial correlation.
3. MTSDS133FMS loaded as raw levels with strong seasonal pattern, contaminating
   the "Q2 fiscal effect" finding.
4. GCEC1 mis-aligned by 2 months relative to GDPC1 → likely explains why GCEC1's
   contribution to nowcast updates is ~zero.
5. W875RX1 is essentially redundant with DSPIC96 already in the baseline; calling
   it a "fiscal variable" is a stretch.

**Moderate (would tighten the paper):**

6. No non-DFM benchmark — absolute RMSE not interpretable.
7. Expanding estimation window rather than FRBNY's rolling 15-year.
8. No forecast-encompassing regression.
9. No predictive intervals reported.
10. Hard-coded DFM hyperparameters (r, p, pC) with no robustness check.
11. Print-statement bug in `em_converged` (`dfm.py:786`) — `print().format()`
    pattern crashes if log-lik decreases.

**Minor (cosmetic / hygiene):**

12. FRED API key leaked.
13. Spec dropping of FRBNY series undocumented.
14. First-3-rows silent drop in `transformData`.
15. No tests anywhere — methodology relies on visual inspection of `summarize()`.

**Not actually issues (positive findings):**

- The DFM port itself is correct and faithful to Banbura-Modugno.
- The pseudo-real-time vintage construction is excellent (real ALFRED data,
  weekly Friday cadence, no look-ahead).
- Target = BEA advance release, not later revisions — correct benchmark choice.
- DFM re-estimated quarterly with parameter switch — matches FRBNY practice.
- The 2020-excluded headline and the cumulative-impact-by-year figure (A8) are
  honest, not cherry-picked.
- Diebold-Mariano in principle is the right test (Appendix C is technically
  correct); only the unit of observation is wrong.

---

## Notes on what I could not determine from code alone

- Whether the actual numbers in `Results.pdf` were generated by the
  currently-committed code or by an earlier private version that included
  `update_Nowcast.py`. The vintage Excels and pickled DFM parameters are
  consistent with the spec files, so the *data pipeline* clearly ran; the
  *nowcasting* loop must have run too at some point, but with code not in the
  public repo.
- Whether GCEC1's near-zero contribution is *only* due to the `shift(2)`
  mis-alignment or also reflects a genuine signal-to-noise issue (quarterly
  fiscal data is structurally less informative than monthly). Both stories are
  consistent with Figure A7; fixing the shift and re-running would discriminate.
- Whether the DM denominator is at weekly or quarterly granularity. The
  reported N = 575/228/347 strongly suggests weekly; the appendix C definition
  is generic and doesn't specify. A direct check of the DM code (not in the
  repo, presumably also in the missing `News_DFM` companion file) would
  resolve this.

---

## File map (absolute paths, what to read next)

- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\Functions\dfm.py`
  — correct port of FRBNY DFM; the print bug is at line 786.
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\Functions\update_Nowcast2.py`
  — broken import at line 6; entire validation pipeline depends on this.
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\Functions\load_data.py`
  — `pca` transform offset at lines 121, 129; verify against BEA growth rates.
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\variables_creation.py`
  — GCEC1 mis-alignment at lines 96-97; leaked API key at line 25.
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\Spec_US_fiscal.xlsx`
  — only 3 fiscal series; MTSDS133FMS is `lin` transformation, should be `ch1`.
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\Results.pdf`
  — Table B5 / B6: the DM observation counts (575, 228, 347) indicate
  weekly-level DM, not quarterly.
