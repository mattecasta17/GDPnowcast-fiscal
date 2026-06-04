# Phase 4 — `(advance−1)` headline nowcast step (design, 2026-06-04)

**Status:** design, approved for spec review (brainstorming → writing-plans).
**Scope:** the FIRST Phase-4-body step — build the machinery for the headline
pre-advance nowcast and wire it for **2017Q1 only** (regression against the
already-measured oracle). The remaining `CONFIG_*` quarters, the fiscal variant,
the RMSE/MAE table and the contaminated-quarter contrast are explicitly later steps.

**Gate context:** the Phase 4.0 gate (CLOSED 2026-06-04) decided the headline is
scored at an as-of **`(advance_date − 1 day)` pre-advance cutoff** on the fuller v2
panel (`US_new`/`US_fiscal`). See
`docs/plans/2026-06-04-phase4.0-release-day-cutoff-decision.md` and
`docs/plans/2026-06-04-phase4.0-data-panel-decision.md`. This spec implements the
*mechanism* of that decision.

---

## Goal

For a quarter `Q`, produce a single **headline nowcast**: the model's GDP nowcast
computed from the vintage as-of `advance_date(Q) − 1 day`, i.e. the tightest as-of
that provably excludes the BEA GDP advance *and its same-day co-releases*. This is
the figure that will be scored against the realized advance (`error = gdp_actual −
y_new`) in the multi-quarter backtest.

`advance_date(Q)` = the first ALFRED `realtime_start` of `Q`'s GDP observation
(the real BEA advance date; varies by quarter — Fri/Thu). For **2017Q1** it is
**2017-04-28** → the cutoff vintage is **2017-04-27**.

## Why a standalone point nowcast (not a news pairing)

In `news.py`, `y_new` is the smoothed nowcast of the target,
`para_const(X_new, Res, 0)["X_sm"][t_nowcast, i_series]` — a function of the **new
vintage and the params only**. The old vintage in `update_nowcast` affects only the
news decomposition (`y_old`, `impact_*`), not `y_new`. So the headline level is
fully determined by the `(advance−1)` vintage + the quarter's params; no old/new
pairing is needed.

Computing it standalone (rather than via `update_nowcast` paired against the last
weekly Friday) has three advantages:

1. **No crash cases.** `update_nowcast` raises on no-news weeks (`None − None`
   `TypeError`) and on the GDP-observed shape bug (`ValueError`). At `(advance−1)`
   the target GDP cell is NaN by construction (the advance has not been released),
   so we are squarely in the genuine-FORECAST case — but pairing against an
   arbitrary prior vintage could still hit a no-news `TypeError`. Standalone avoids
   it entirely.
2. **Conceptually correct.** The headline is a *level* nowcast as-of a date, not the
   "news since last week".
3. **`update_nowcast` stays untouched** → the v1-parity goldens
   (`test_runner_golden`, `test_news_golden`) remain byte-identical.

## Free regression oracle

`tools/release_day_leak_scan.py run` already built the 2017-04-27 vintage (into
`US_new_thu`, same `build_vintage`) and ran the Thursday arm: `y_new = 2.246138`.
Because `y_new` is old-vintage-independent, the standalone headline on the same
2017-04-27 data + same `res_curr` params **must** reproduce `2.246138`. That is the
regression test for this step.

---

## Components

### a) Config — `QuarterCfg.advance_date`

Add one field to `src/gdpnowcast/nowcast/config.py`:

```python
advance_date: str  # real BEA advance date (first ALFRED realtime_start of Q's GDP); ISO
```

Set `CONFIG_2017Q1.advance_date = "2017-04-28"`. The cutoff vintage filename is
derived in the runner as `advance_date − 1 day` (= `"2017-04-27"`), keeping the
documented `−1` rule explicit in code rather than hard-coding the offset date.

### b) Build tool — `tools/build_headline_vintages.py`

A dev tool (not CLI-wired yet), mirroring `release_day_leak_scan`'s build pattern,
reusing `fetch_release_history` / `build_vintage` / `write_vintage`:

1. fetch the release histories for all baseline series once (cached in a dict, as in
   `release_day_leak_scan.build`);
2. from the GDP history compute `advance_date(Q)` =
   `gdp.groupby("date")["realtime_start"].min()` for `Q`'s observation (FRED-native
   quarter-start obs date, e.g. `2017-01-01` for 2017Q1);
3. **assert** the computed `advance_date` matches `CONFIG_2017Q1.advance_date`
   (auditable guard against a stale hand-entered date);
4. `write_vintage(build_vintage(histories, specs, advance_date − 1), data/US_new,
   advance_date − 1)` → `data/US_new/2017-04-27.xlsx`.

The file lands in `data/US_new` alongside the Friday manifest (same builder, same
panel; gitignored). ALFRED is hit only at build time; the backtest reads the file
offline.

### c) Smoother helper — `news.nowcast_point`

New, standalone function in `src/gdpnowcast/news.py` (does **not** modify
`update_nowcast`):

```python
def nowcast_point(
    X_new: np.ndarray, Time: pd.DatetimeIndex, Spec: DfmSpec,
    Res: dict, series: str, period: str,
) -> float:
    ...
```

It replicates exactly the relevant lines of `update_nowcast`: append 12 months of
NaN to `X_new`, extend `Time` by 12 `MonthBegin` steps, resolve `t_nowcast` and
`i_series`, then return
`float(para_const(X_new, Res, 0)["X_sm"][t_nowcast, i_series][0])`. No masking
branch (target is NaN by construction), no old vintage, no news decomposition.

### d) Runner — headline step on `df.attrs`

In `run_quarter` (`src/gdpnowcast/nowcast/runner.py`), after the weekly loop, compute
the headline from the `(advance−1)` vintage reusing the already-estimated
`res_curr` (advance−1 is within the quarter → past `switch_date` → curr params):

```python
adv_minus_1 = (pd.Timestamp(cfg.advance_date) - pd.Timedelta(days=1)).date().isoformat()
xh, timeh, _ = load_vintage(_vfile(data_subdir, adv_minus_1), spec)  # full sample, like the news step
y_head = nowcast_point(xh, timeh, spec, res_curr, series, cfg.period)
df.attrs["headline"] = {"vintage": adv_minus_1, "y_new": y_head, "error": cfg.gdp_actual - y_head}
```

The weekly loop and its output `DataFrame` are unchanged → existing goldens
unaffected. The headline rides on `df.attrs["headline"]`, consistent with how the
runner already exposes `df.attrs["skipped"]`.

### e) Tests — `tests/test_runner_headline.py` (marked `slow`)

1. **Regression:** `run_quarter(CONFIG_2017Q1, "US_new", "Spec_US_new.xlsx", "GDPC1")`
   then `df.attrs["headline"]["y_new"] == pytest.approx(2.246138, rel=1e-6)` and
   `df.attrs["headline"]["vintage"] == "2017-04-27"`.
2. **Look-ahead guard:** read `data/US_new/2017-04-27.xlsx`; assert the `GDPC1` cell
   at the 2017Q1 target row (`2017-03-01`, last-month-of-quarter stamping) is
   **NaN** — i.e. the headline is a genuine forecast, not a read-back of the advance.
   (Mirrors `release_day_leak_scan._gdp_at_q1`.)

Both depend on `data/US_new/2017-04-27.xlsx` existing → the test is `slow` and lives
in the `just test-golden` heavy lane (like `test_runner_masked`); document that the
build tool must be run first to produce the vintage. `just ci` (fast lane) is
unaffected.

---

## Out of scope (later Phase-4 steps)

- Wiring the remaining `CONFIG_*` quarters and the fiscal variant (`US_fiscal`).
- The contaminated-quarter contrast (e.g. 2025Q1) that actually *exhibits* the
  co-release leak — needs a second quarter wired.
- The full 2017-2025 RMSE/MAE headline table and the leak's pp effect-size.
- The `pca(GDPC1)` vs BEA-growth regression test and the two methodology fixes
  (MTSDS133FMS→`ch1`, DM quarterly+HLN).

## Risks / notes

- **Build-tool network dependency:** building the 2017-04-27 vintage needs a working
  `FRED_API_KEY` (`load_dotenv(override=True)`; napkin Tooling #3). Once built, the
  test runs offline.
- **OneDrive venv lock** on `uv` editable rebuilds — self-heals on retry
  (napkin Tooling #1).
- The `2.246138` oracle is pinned at 7 significant figures (the `rtol=1e-6`
  resolution limit, same rationale as the masking pin); chasing more digits is false
  precision.
