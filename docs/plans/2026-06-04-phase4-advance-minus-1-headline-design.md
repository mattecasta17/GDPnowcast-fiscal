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

In `news.py`, in the branch that fires for a pre-advance vintage — the FORECAST case
*with new information* (`news.py:234-258`: `Res_new = para_const(X_new, Res, 0)`,
`y_new = Res_new["X_sm"][t_fcst, v_news]`) and the already-observed case
(`news.py:182-196`: `y_new = X_new[t_fcst, v_news]`) — `y_new` is a function of the
**new vintage and the params only**. (The one exception is the FORECAST *no-new-info*
sub-branch, `news.py:220-232`, which sets `y_new = y_old.copy()` off `X_old`; that
path requires identical old/new NaN patterns and is unreachable for a single-vintage
level nowcast.) So a standalone smooth of the `(advance−1)` vintage reproduces the
`y_new` `update_nowcast` would compute for it; no old/new pairing is needed.

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
`US_new_thu`, same `build_vintage`) and ran the Thursday arm, which goes through the
FORECAST-with-new-info branch (`y_new = para_const(X_new)`) and reported
`y_new = 2.246138`. Since the standalone `nowcast_point` computes exactly that same
single-vintage smooth on the same 2017-04-27 data + same `res_curr` params, it **must**
reproduce it. On this *clean* quarter the `(advance−1)` genuine forecast also equals
the Friday+mask and Thursday arms (the cutoff-decision doc's 2017Q1 table: all three
= `2.246138`), so it matches the value the masked test already pins,
`2.2461378` (`test_runner_masked.py:47`). That equality is the regression test.

---

## Components

### a) Config — `QuarterCfg.advance_date`

Add one field to `src/gdpnowcast/nowcast/config.py`:

```python
advance_date: str  # real BEA advance date (first ALFRED realtime_start of Q's GDP); ISO
```

`QuarterCfg` is `@dataclass(frozen=True)` (`config.py:18`), so this is a **constructor
kwarg** on the `CONFIG_2017Q1(...)` call — `advance_date="2017-04-28"` — **not** a
post-hoc `CONFIG_2017Q1.advance_date = ...` assignment (which would raise
`FrozenInstanceError`). Add it as a required field (no default): `CONFIG_2017Q1` is
the only constructor, and `replace(CONFIG_2017Q1, vintages=...)` in
`release_day_leak_scan.py:115` preserves the new field. The cutoff vintage filename is
derived in the runner as `advance_date − 1 day` (= `"2017-04-27"`), keeping the
documented `−1` rule explicit in code rather than hard-coding the offset date.

### b) Build tool — `tools/build_headline_vintages.py`

A dev tool (not CLI-wired yet), mirroring `release_day_leak_scan`'s build pattern,
reusing `fetch_release_history` / `build_vintage` / `write_vintage`:

1. load the **data** spec — `gdpnowcast.data.spec.load_spec(SPEC_PATHS["baseline"])`
   → `list[SeriesSpec]` (the one `build_vintage` consumes), **not** the DFM
   `load_dfm_spec` → `DfmSpec`; the two are easy to confuse. Fetch the release
   histories for all those series once (cached in a dict, as in
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

It replicates exactly the relevant lines of `update_nowcast` (`news.py:65-90`):
append the `(12, N)` NaN block to `X_new`, extend `Time` by 12 `MonthBegin` steps,
resolve `i_series` (`np.where(series == Spec.SeriesID)[0]`) and `t_nowcast` (the freq
branch, including the `t_nowcast.size == 0` raise), then return
`float(para_const(X_new, Res, 0)["X_sm"][t_nowcast, i_series][0])`. The 12-month
extension **must** happen *before* `para_const`: even though `2017-03-01` is already
within the original `Time` (so `t_nowcast` is unchanged), `para_const` standardizes
and smooths over `T = X.shape[0]` (`news.py:413,416,443`), so the appended rows are
part of the path that produced the `2.246138` oracle — an implementer must not
"optimize away" the inert-looking extension. No masking branch (target is NaN by
construction), no old vintage, no `X_old` size-matching, no news decomposition.

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

`res_curr` is correct for 2017Q1 because `2017-04-27 ≥ switch_date (2017-01-01)` — the
same branch `runner.py:58` takes. This holds for every quarter (an `(advance−1)` cutoff
is always within its own quarter, hence past that quarter's `switch_date`), but when
the later quarters are wired prefer reusing the switch expression
(`res_prev if pd.Timestamp(adv_minus_1) < switch else res_curr`) over a hardcoded
`res_curr`, to avoid a latent assumption.

### e) Tests — `tests/test_runner_headline.py` (marked `slow`)

Both tests read the gitignored, must-be-built `data/US_new/2017-04-27.xlsx`, so the
module **must** carry a skip guard mirroring the existing heavy tests
(`test_runner_masked.py:14-17`, `test_runner_golden.py:13-17`):

```python
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not Path("data/US_new/2017-04-27.xlsx").exists(),
        reason="(advance-1) headline vintage not built (run tools/build_headline_vintages)",
    ),
]
```

Without it the test *fails* (FileNotFoundError) rather than *skips* wherever the
vintage is absent (CI, every fresh clone) — the same gating the v1-data tests use.

1. **Regression:** `run_quarter(CONFIG_2017Q1, "US_new", "Spec_US_new.xlsx", "GDPC1")`,
   then `df.attrs["headline"]["vintage"] == "2017-04-27"` and
   `np.testing.assert_allclose(df.attrs["headline"]["y_new"], 2.2461378, rtol=1e-6,
   atol=1e-6)` — the **same literal and tolerance** as `test_runner_masked.py:47`
   (single source of truth; they must coincide on this clean quarter, see the oracle
   section). Note this is the first test to exercise the real `US_new` (v2 panel)
   headline path; the masked/golden tests run on `US_new_v1`.
2. **Look-ahead guard:** read `data/US_new/2017-04-27.xlsx`; assert the `GDPC1` cell
   at the 2017Q1 target row (`2017-03-01`, last-month-of-quarter stamping) is
   **NaN** — i.e. the headline is a genuine forecast, not a read-back of the advance.
   (Mirrors `release_day_leak_scan._gdp_at_q1`.)

The test is `slow` and lives in the `just test-golden` heavy lane (like
`test_runner_masked`); the build tool must be run first to produce the vintage. In CI
(no built vintage) it skips, consistent with the v1-data-gated tests. `just ci` (fast
lane) is unaffected.

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
- The oracle is pinned to the committed `2.2461378` literal at `rtol=atol=1e-6` (the
  resolution limit, same rationale as the masking pin); chasing more digits is false
  precision. The `US_new` (v2-panel) headline value rounds to `2.246138` per the
  cutoff-decision table, comfortably inside that band — but the test is itself the
  confirmation; if it ever lands outside `1e-6`, that is a finding to surface, not to
  loosen away.
