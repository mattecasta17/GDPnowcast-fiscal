# Verified audit findings — synthesis

**Date:** 2026-05-11
**Branch:** `refactor/v2` (HEAD `c351c75`)
**Method:** 5 independent verification agents, each given one finding + a self-contained brief. Reports in this directory.

This file consolidates the verification outcomes and the implications for the v2 plan (`docs/plans/2026-05-11-v2-design.md`).

---

## Outcomes at a glance

| # | Finding (from v1 audit) | Verdict | Report |
|---|---|---|---|
| 1 | GCEC1 mis-aligned by 2 months vs GDPC1 | **REFUTED** | [02_gcec1_misalignment.md](02_gcec1_misalignment.md) |
| 2 | MTSDS133FMS un-deseasonalised (`lin` instead of `ch1`) | **CONFIRMED** | [03_mtsds_seasonality.md](03_mtsds_seasonality.md) |
| 3 | DM tests at weekly granularity (N=575 instead of T≈30) | **CONFIRMED** (+ stacked bug: no HAC despite Appendix C) | [04_dm_weekly_granularity.md](04_dm_weekly_granularity.md) |
| 4 | W875RX1 mis-labelled as fiscal, redundant with DSPIC96 | **PARTIALLY CONFIRMED** (mislabel yes; redundancy no on `pch`) | [05_w875rx1_redundancy.md](05_w875rx1_redundancy.md) |
| 5 | `Functions/update_Nowcast.py` missing → pipeline broken | **CONFIRMED** (recoverable from git `729b40b`) | [01_reproducibility.md](01_reproducibility.md) |
| 6 | FRED API key leaked at `variables_creation.py:25` | **CONFIRMED** | [01_reproducibility.md](01_reproducibility.md) |

Net: 3 confirmed as-stated, 1 confirmed + extra bug, 1 partially confirmed, 1 refuted.

---

## What changes in the v2 design doc

### Phase 3 (Library migration) — reproducibility recovery

**Add:** `update_Nowcast.py` is recoverable from this repo's own git history.
```
git show 729b40b:Functions/update_Nowcast.py > src/gdpnowcast/news.py  # then port
```
The v2 design's contingency of "re-implement from Bok et al. App. or upstream `MajesticKhan/Nowcasting-Python`" is no longer needed. The lost file was committed in `729b40b "Nowcast"` (2025-12-03 17:07:55 UTC), 431 lines, contains `def News_DFM` at line 122, `def update_nowcast` at line 10, `def para_const` at line 347. Explicitly deleted 16 minutes later in `e0928d5`, almost certainly an accidental bundle with an `.idea/` cleanup. Reachable from both `main` and `refactor/v2`.

### Phase 4 (Methodology fixes) — REVISE

| Phase 4 item (current design) | Status after verification |
|---|---|
| Fix GCEC1 shift (`remove the shift(2)`) | **REMOVE FROM PLAN.** The shift is the correct ingestion of FRED's quarter-start stamp into the project's "third-month-of-quarter" convention. Removing the shift would silently delete GCEC1 (not misalign it), because `pca` reads rows `2, 5, 8, …` and unshifted GCEC1 would land on `0, 3, 6, …` → NaN. |
| MTSDS133FMS → `ch1` | **KEEP.** Empirically confirmed: April is +1.13σ vs other months on raw `lin`; `ch1` shrinks the gap to 0.12σ (9× reduction). |
| DM at quarterly with HLN | **KEEP, EXPAND.** DM code lives in `dashboard_nowcast_fiscal.py:1324-1417` (not in the missing `update_Nowcast.py`). Two bugs stacked: (a) weekly granularity (N=652 = 34 quarters × 19.17 weekly vintages); (b) `scipy.stats.ttest_1samp` only — no HAC, no HLN — despite Appendix C of the thesis explicitly claiming HAC variance. Quarterly-level DM with HLN correction would drop the headline 6.40 ex-2020 stat to ~1.46 (borderline). |
| Drop W875RX1 from fiscal | **REPLACE with: recategorise W875RX1.** Mislabel claim is correct — W875RX1 is *market* income by construction (transfers stripped). Redundancy claim is refuted: on `pch` (the actual transform used) the correlation with DSPIC96 is 0.09 full-sample, with the largest divergences in fiscal-transfer episodes (CARES 2020-04, ARP 2021-03) — exactly the regime the fiscal extension exists to capture. Action: keep series in the spec, change `Category` from `Fiscal` to `National Accounts`, add a note. Drop the "considered but rejected" narrative. |
| (new) Fix DSPIC96 SeriesName | **ADD.** Both specs label DSPIC96 as "Personal Income". It is Real Disposable Personal Income. Cosmetic but worth fixing alongside the other spec edits. |

### Phase 1 (Foundation) — FRED key

Confirmed: `variables_creation.py:25` hardcodes `"64b47ef802cce7ec9c8b65d476e9a8ea"` as a fallback. The string appears once in source. Introduced in commit `729b40b`. No `.gitignore`, no `.env`, no `.env.example` exist at HEAD. Burned because the repo has a public GitHub remote (`origin/main`, merged PR `#1`).

**Action items:**
1. Rotate the key at FRED's portal.
2. Replace the `or "..."` fallback with `raise RuntimeError("FRED_API_KEY not set")`.
3. Add `.gitignore` (entries: `.env`, `data/`, `outputs/`, `*.pickle`, `__pycache__/`).
4. Add `.env.example` with `FRED_API_KEY=`.
5. **Consider but probably skip** a `git filter-repo` history rewrite — once the key is rotated, the burned value is harmless; rewriting history breaks every fork/clone.

### Phase 5 (Portfolio polish) — recompute headline numbers

Once Phases 3 and 4 are done, **the headline RMSE/MAE tables in `docs/results.md` will move materially**:
- Bug #2 (MTSDS133FMS `ch1`) likely collapses the "Q2 fiscal effect" finding.
- Bug #3 (proper quarterly DM + HLN) likely demotes all "fiscal significantly improves nowcast" results from p ≈ 0.0001 to borderline/non-significant.
- Bug #4 unchanged (W875RX1 stays in spec), so net signal slightly preserved.

Honest narrative shift, not catastrophic: from "fiscal helps Q2 and post-2020" → "fiscal carries non-redundant transfer-cleaned income signal but does not significantly outperform baseline at standard significance levels". Still a publishable finding for a careful nowcasting paper.

---

## Notable agent discoveries beyond the v1 audit

1. **`update_Nowcast.py` is recoverable from git history** (`729b40b`). Saves Phase 3 time.
2. **DM code lives in `dashboard_nowcast_fiscal.py`, not the missing module.** The v1 audit's localisation was wrong; the finding was right.
3. **Plain t-test masquerading as HAC.** `dm_test(series)` at `dashboard_nowcast_fiscal.py:1377-1379` is `scipy.stats.ttest_1samp`. The thesis Appendix C (p. 42 of Results.pdf) claims HAC. Phase 4 should reconcile.
4. **DSPIC96 mis-named in both specs** ("Personal Income" → should be "Real Disposable Personal Income").
5. **The audit contradicts itself on the shift.** `03_methodology_audit.md` lines 319-331 say GDPC1 is at 2024-01-01 (mis-alignment story); lines 388-405 in the same file correctly say GDPC1 is at 2024-03-01 in the vintage Excel. The first framing is wrong; the second is right. The "shift = bug" Bug #1 derives from the wrong framing.

---

## Implication for v1's headline conclusion

After Phase 4 (with the corrected list of fixes above), the expected impact on the thesis's headline finding "fiscal variables improve GDP nowcasting, especially Q2 and post-2020":

- "Especially Q2" — **likely collapses** when `ch1` removes the April seasonal spike.
- "Significantly improves" — **likely collapses** when DM is run quarterly with HLN (+ HAC).
- "Adds non-redundant information" — **likely survives**, because W875RX1's `pch` correlation with DSPIC96 is 0.09 and it diverges precisely during fiscal-transfer episodes.

So the v2 paper narrative becomes "the fiscal extension carries genuine non-redundant signal but the improvement is marginal and not statistically significant at conventional thresholds without a much longer sample" — more honest, more defensible.

---

## Verification methodology note

Each agent was dispatched with:
- The specific audit claim to verify
- The exact files/lines to inspect
- A required verdict format (CONFIRMED / PARTIALLY CONFIRMED / REFUTED) with concrete evidence
- An output path under `docs/audit/v1-verified/`
- An instruction not to delegate further

Agents ran in parallel and independently. None coordinated. Two agents independently reached the same conclusion about the DSPIC96 SeriesName mislabel (#5 above — not in the original audit scope), which is a useful corroboration.

Re-verification recipes are included in each report's "Commands run" section.
