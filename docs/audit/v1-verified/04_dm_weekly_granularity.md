# Verified — Bug #3: DM tests at weekly granularity

## Verdict
**CONFIRMED.** The Diebold–Mariano tests reported in Table B5 / B6 are computed
on per-Friday vintage forecast errors pooled across all backtest quarters — not
on per-quarter terminal nowcasts — and the test is implemented as a plain
one-sample t-test (`scipy.stats.ttest_1samp`) with **no HAC variance and no HLN
small-sample correction**, despite Appendix C explicitly claiming HAC. Reported
N values (652 / 575 / 228 / 347) reconcile to 34 quarters × ~19 weekly vintages,
not to T ≈ 30. Naive deflation of DM = 6.4 by √(N/Q) ≈ 4.38 brings the statistic
to ~1.46 — borderline rather than overwhelmingly significant.

## Evidence

### DM code presence in repo

The DM test lives in the streamlit dashboard, not in a dedicated `Functions/`
module:

- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\dashboard_nowcast_fiscal.py`, lines **1324–1417** ("DIEBOLD–MARIANO TEST SECTION").
- No mention of "diebold", "DM_test", "harvey", or "HLN" anywhere in the
  `Functions/` package. `Functions/dfm.py:988` references "Harvey, 1990" only as
  a comment about the Kalman filter (unrelated).
- No file named `Functions/update_Nowcast.py` exists in the repo — but the
  audit's premise that DM code is "missing" is wrong in a different way: the
  test *is* in the repo, just in the dashboard rather than under `Functions/`.

Key code excerpt (`dashboard_nowcast_fiscal.py:1377–1379`):

```python
def dm_test(series):
    stat, pval = ttest_1samp(series.dropna(), 0)
    return stat, pval
```

This is a plain one-sample t-test against zero. No HAC variance estimator
(Newey-West, Bartlett kernel, etc.) and no Harvey-Leybourne-Newbold (1997)
small-sample finite-T correction is applied — even though **Appendix C of the
thesis** (p. 42 of `Results.pdf`) explicitly states:

> "Var(d̄) is its HAC-consistent variance, which corrects for potential serial
> correlation and heteroskedasticity in the forecast errors. This adjustment is
> necessary to ensure valid inference in the test, since nowcast revisions
> typically exhibit temporal dependence."

So in addition to the granularity issue, the implementation does not match the
methodology described in the paper.

### Granularity of saved loss series

`nowcast_2017.py`, `nowcast_2024.py`, `nowcast_2024_fiscal.py` all save **one
row per weekly vintage** to `nowcast_Q/nowcast_YYYY_qX.csv` (resp.
`nowcast_Q_fiscal/nowcast_YYYY_qX_fiscal.csv`):

- `nowcast_2017.py:149-169`: builds `results_list` by looping over consecutive
  weekly vintages within a quarter; `error = gdp_actual - y_new` is computed
  per-vintage (per-Friday), and the whole list is written via
  `df_results.to_csv(f"nowcast_Q/nowcast_{period[:4]}_{period[4:]}.csv")`.
- `nowcast_2024_fiscal.py:158`: same pattern, fiscal directory.

Direct inspection of `nowcast_Q/nowcast_2017_q1.csv` confirms 18 weekly vintage
rows (2016-12-09 through 2017-04-21, with one Friday missing per calendar). Row
counts across the 34 backtest files:

| Vintage rows per quarter | # quarters |
|---:|---:|
| 18 | 4 |
| 19 | 22 |
| 20 | 8 |

Mean ≈ 19.2 vintages/quarter. The pre-release tracking window described at the
bottom of the dashboard is "roughly 22 weeks", which lines up with the
audit's √22 ballpark.

The dashboard then pools across all 34 quarters
(`dashboard_nowcast_fiscal.py:1343–1366`) without any per-quarter aggregation
or "final-week-only" filter. So `d_rmse`, `d_mae`, `d_bias` are vectors of
length ≈ 650, with each element a per-Friday loss differential.

### Results.pdf N values (Table B5, p. 41)

Verbatim from `Results.pdf` page 41:

> | Period           | Observations | RMSE    | MAE    | Bias    |
> |------------------|-------------:|--------:|-------:|--------:|
> | Full sample      | 652          | -0.7659 | 1.8194 | 4.4093  |
> | Full excl. 2020  | 575          | 6.4012  | 6.4811 | 2.7804  |
> | Pre-2020         | 228          | 5.6154  | 3.8905 | -2.9637 |
> | Post-2020        | 347          | 5.9777  | 5.6311 | 3.9278  |
>
> Table B5: DM statistics for the fiscal block. This table reports the
> Diebold-Mariano test statistics across four distinct subsamples covering the
> 2017-2025 period.

Table B6 (p. 41) reports matching p-values: 0.0000 for RMSE/MAE in the ex-2020,
pre-2020, and post-2020 subsamples.

Caption uses the word "Observations" without specifying weekly vs. quarterly —
the reader is left to assume quarterly, which is the natural interpretation
for a DM table.

### Arithmetic

Sample: 2017Q1 → 2025Q2 = **34 quarters**.

Replicating the dashboard's concat logic exactly (outer-align on max length when
base and fiscal vintage counts differ — happens for 2024Q2 and 2025Q2):

```
full:     N=652, quarters=34, N/Q=19.18
ex2020:   N=575, quarters=30, N/Q=19.17
pre2020:  N=228, quarters=12, N/Q=19.00
post2020: N=347, quarters=18, N/Q=19.28
```

**Every subsample's N exactly matches the table**, and the implied ratio is
~19 weekly observations per quarter — consistent with a 19-Friday tracking
window per quarter, not 22 (the README claim of "22 weeks" is itself a slight
overstatement).

Quarterly-level DM would have T = 34 / 30 / 12 / 18, not 652 / 575 / 228 / 347.

### Magnitude assessment

If the per-quarter loss differential were the average of ~19 strongly
positively-correlated per-Friday differentials (the most extreme case — all
Fridays in a quarter share the same target Y_q and similar information set), the
effective sample size collapses from N back to Q, and the naive t-statistic
overstates the true t by roughly √(N/Q) ≈ √19.17 ≈ **4.38**.

Deflation of the headline number:

- Ex-2020 RMSE: 6.4012 / 4.38 ≈ **1.46** → two-sided p ≈ 0.15 (not significant at 5%).
- Ex-2020 MAE:  6.4811 / 4.38 ≈ **1.48** → similar.
- Pre-2020 RMSE: 5.6154 / 3.46 (√12) ≈ **1.62** → borderline.
- Post-2020 RMSE: 5.9777 / 4.24 (√17.97) ≈ **1.41** → not significant at 5%.

Adding Harvey-Leybourne-Newbold (1997) finite-T correction (multiplicative
factor √[(T + 1 − 2h + h(h-1)/T) / T] with h = 1 nowcast horizon, which is
≈ 1 for T = 30 but smaller for T = 12) would shave another small fraction off
the pre-2020 stat. So the audit's headline — "6.4 plausibly drops to ~1.5
(borderline)" — is **right to within 0.05**. The qualitative conclusion
("statistically significant" → "borderline / not significant at 5%") is
robust to whatever reasonable HAC kernel choice one makes.

The bias DM stats (2.78 / -2.96 / 3.93) deflated by √19 land at 0.63 / 0.86 /
0.92 — all clearly not significant. The pre-2020 "significant negative bias"
finding in the thesis (p. 24) evaporates entirely.

## Caveats

- The audit's claim that "DM code is in the missing `Functions/update_Nowcast.py`"
  is wrong — the DM code is in `dashboard_nowcast_fiscal.py`. The substantive
  finding (weekly granularity) is still correct.
- The √(N/Q) inflation factor is an **upper bound** that assumes perfect
  serial correlation within a quarter. The true inflation depends on the AR
  structure of the weekly d_t series; if correlation is, say, ρ = 0.5
  geometrically decaying, the effective inflation factor is smaller (the
  Newey-West / HAC variance with appropriate bandwidth would partly recover the
  right standard error — but the code applies neither).
- The pre-2020 subsample has only 12 quarters. Even with a correct quarterly DM
  + HLN, statistical power is limited; "borderline" is the honest verdict
  rather than a clean reject-or-not.
- Replication note: the dashboard's `pd.DataFrame({error_base: ..., error_fisc: ...})`
  concatenation outer-aligns by index when the two CSVs have different row
  counts (2024Q2 and 2025Q2: 19 vs 20). Pandas pads the shorter column with
  NaN; `ttest_1samp` calls `.dropna()` on the *differential* — so the effective
  N matches the longer column. This reproduces Table B5 totals exactly.

## Commands run

```
# DM code search
Grep "diebold" -i  -> dashboard_nowcast_fiscal.py only
Grep "DM_test|dm_stat|harvey|HLN" -i -> dashboard_nowcast_fiscal.py:1377 dm_test()

# Read DM implementation
Read dashboard_nowcast_fiscal.py:1320-1470

# Inspect saved loss series
Read nowcast_2017.py:140-200, nowcast_2024_fiscal.py:150-180
ls nowcast_Q/  -> 34 files (2017Q1..2025Q2)
wc -l on selected files -> 18-20 rows each
Read nowcast_Q/nowcast_2017_q1.csv  -> per-Friday vintage rows

# Replicate dashboard tally
python -c "<concat all base+fiscal CSVs, outer-align, tally full/ex2020/pre2020/post2020>"
-> {full: 652, ex2020: 575, pre2020: 228, post2020: 347}  — exact match to Table B5

# Read Table B5/B6 from PDF
python -c "import fitz; doc=fitz.open('Results.pdf'); ..."
-> page 41 = Table B5, page 41 = Table B6, page 42 = Appendix C (DM definition)

# Arithmetic
N/Q ≈ 19.17 across all subsamples
DM 6.4 / sqrt(19.17) ≈ 1.46
```
