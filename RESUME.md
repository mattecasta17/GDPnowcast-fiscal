# RESUME — where we left off

**Last touched:** 2026-06-03 (**Phase 3 baseline-2017q1 COMPLETE** — A4 + B1–B8 DONE: the full v1 chain `dfm_spec/transform/_dfm_support/dfm/news/decomposition` **plus** the parameterised `nowcast/runner` are ported, de-MATLAB-ized, golden parity `1e-6`. B1–B6 pushed (`1b3bec2`); the gate/docs commit `bb0ce9d` + B7 `06363f0` + B8 are **LOCAL, not pushed** — **final sweep review pending before push**. After push, next is the **Phase 4.0 evaluation-methodology gate**, see the 🔵 block.)
**Branch:** `refactor/v2` (off main `d50a2bc`). ⛔ **NEVER merge into `main`** — v2 lives permanently on this branch (Matteo's hard rule).
**Status:** ✅ **Phase 1 (Foundation) complete and pushed.** On 2026-05-31 the red-team backlog was triaged (5 critical + 3 sequencing accepted), folded into the design doc + Phase 1 plan, then Phase 1 was executed inline: src-layout skeleton, `uv`/`ruff`/`mypy`/`pytest`/`pre-commit`/`just`/GitHub-Actions tooling, `.gitignore`, data untracked (1300→54 tracked files, 1.65 MB), FRED-key fallback patched + `.env.example`, README (confidence-framed + CI badge), `update_Nowcast.py` recovered from git. `just ci` green (lint + mypy + 2 smoke tests). Three environment deviations applied (justfile `windows-shell`, CI uv `0.11.x`, pyproject `[tool.uv] link-mode = "copy"` for OneDrive) — see the Phase 1 plan's "Executed 2026-05-31" note.

**✅ FRED key rotated (2026-06-01).** New key generated on the existing FRED account, stored in local `.env` only, and confirmed working (`get_series_info("GDPC1")` → OK). Gotcha for next time: a stale `FRED_API_KEY` Windows **User** env var (`3b80…`) shadowed `.env` because `load_dotenv` doesn't override existing env vars — fixed by removing the User var + using `load_dotenv(override=True)` in data-layer loaders. See napkin Tooling #3.

**✅ Pre-Phase-2 ALFRED-coverage spike PASSED (2026-06-01) — GO 35/35.** `tools/alfred_coverage_spike.py` confirmed all 35 series (32 baseline + 3 fiscal) resolve on FRED, return a non-empty point-in-time as-of series, and have ALFRED vintage history back well before 2016-12-09 (tightest = `MTSDS133FMS` earliest 2015-09-11). **No fallback branch needed** — every series rebuilds directly from ALFRED point-in-time; the design doc §8 risk "some series may lack vintages back to 2016-12" did not materialize.

**⚠️ Environment caveat:** `.venv` (and the repo) sit inside OneDrive, which locks venv files during `uv` reinstalls. Recommend excluding the repo (or at least `.venv`/`data/`) from OneDrive sync before Phase 2's large fetch.

**✅ Phase 2 data layer BUILT + committed (2026-06-01).** New 35-series ALFRED point-in-time fetcher implemented and committed on `refactor/v2` (Tasks 1-8 of `docs/plans/2026-06-01-phase2-implementation.md`): `src/gdpnowcast/data/{spec,vintages,fred,builder}.py` + `gdpnowcast fetch` (CLI) + committed manifests (`configs/vintages_{baseline,fiscal}.csv`, 486 each) + 19 offline tests + 12 network no-leakage cross-validation tests (`reconstruct_asof` vs point-in-time API, `rtol=0/atol=0`) + `docs/data_sources.md` + 3 tools (coverage spike, manifest generator, v1 diagnostic). `just ci` green (19 passed, 2 superset SKIPPED pending fetch, 12 slow deselected). **Two collateral bugs found + fixed while committing:** (a) `.gitignore`'s unanchored `data/` was silently ignoring the whole `src/gdpnowcast/data/` package → anchored to `/data/`; (b) an accidental `.env.example`→`.env` find-replace had corrupted `.env.example`, `variables_creation.py`, `README.md`, and the Phase 1 plan → all reverted.

**✅ Task 9 DONE (2026-06-01) — Phase 2 COMPLETE.** Ran the full fetch: backed up v1 dirs (`data/US_new_v1` 486, `data/US_fiscal_v1` 485), then `gdpnowcast fetch --variant baseline` (486 files) + `--variant fiscal` (486 files) — both built cleanly into `data/US_new` / `data/US_fiscal` (gitignored). Exit verification all green:
- **Superset gate PASSED** for both variants (`tests/test_superset.py`): generated ⊇ manifest.
- **`just ci` green:** 21 passed (incl. both superset tests), 12 slow deselected, ruff + mypy clean.
- **Value comparison vs v1 (Decision D3 — diagnostic, not a gate; `tools/compare_to_v1.py`):** ⚠️ my first report ("0 diff across 11.3M cells, reproduces v1 exactly") was **WRONG** — it only checked cells populated on *both* sides. The symmetric check (Matteo flagged it) found: (a) **shared cells identical** (0 diff); (b) **v2 has ~194.5k more cells of early history** per variant (`PCEC96` 1985 vs v1's 2002; `DGORDER`/`BUSINV` 1985 vs 1992) — contiguous, point-in-time valid, v2 more complete; (c) **v1 mis-stamps the 3 quarterly series in ~10 year-end vintages** (May/Aug/Nov instead of Mar/Jun/Sep) → ~4.3k "v1-only" cells, v2 is the correct/consistent one. Upgraded `compare_to_v1.py` to report the asymmetric directions so this can't re-mask. Full writeup in `docs/data_sources.md`.
- **Cosmetic:** 4 early vintages (`2016-10-03`, `2016-12-02`, `2016-12-07`, `2017-02-03`) carry one extra trailing all-NaN month (the vintage's own empty month v1 trimmed) — no value differs, not look-ahead.
- **⚑ Phase-3 input decision (open):** the longer v2 history WILL move the v2 DFM vs the v1 golden — decide whether to truncate to v1's series starts (isolate methodology from data) or keep the fuller panel.

**✅ Phase 3a GATE PASSED (2026-06-01) — golden frozen from UNMODIFIED v1, validated bit-for-bit.** Plan: `docs/plans/2026-06-01-phase3-implementation.md`. Executed inline with checkpoints:
- **A0 NumPy-2 shims** (`Functions/load_data.py`, `Functions/dfm.py`): the locked NumPy 2.4.6 removed `np.in1d` and turned single-element-array→scalar assignment into an error. Shims = `np.in1d→np.isin` + **`.item()`** on the two `InitCond` `(1,1)` assigns. ⚠️ The plan prescribed `float(...)`, but in NumPy 2 `float()` requires a 0-d array and **raises** on a `(1,1)`; `.item()` is the correct behaviour-preserving extraction. Two infra commits enabled clean legacy commits: ruff `force-exclude=true` + `end-of-file-fixer` excludes `Functions/` (so the v1 tree stays byte-for-byte until its Phase-5b deletion).
- **A2 estimator golden** (`tests/golden/dfm_legacy_estimator.json`, via `tools/freeze_golden.py`): 2 vintages (2016-10-03, 2017-01-03), `sample_start=2000-01-01`, 28 series. **`pickle_max_abs_dC ≈ 5e-15`** vs the committed NumPy<2 production pickles → the A0 shims are bit-for-bit behaviour-preserving and the golden **IS** v1's production numbers. ⇒ **3b parity tolerance stays at the tight default `rtol=atol=1e-6` (no relaxation).**
- **A3 nowcast golden** (`tests/golden/dfm_legacy_nowcast.json`, via `tools/freeze_golden_nowcast.py`): 2017q1, params@2000 + news@full-sample. Faithfully replicates v1's `nowcast_2017.py` blanket try/except skip-on-error → **18 rows, 3 skipped** (all 3 skipped by v1 too). **The 3 skips have TWO distinct causes (VERIFIED 2026-06-03 by running the shimmed v1 stack — the earlier "all None-None" wording was wrong):** (a) **2016-12-30 & 2017-02-24 = no-news weeks** (`v_miss=0`) → `News_DFM` FORECAST SUBCASE (A) returns actual/forecast=None → `None - None` **TypeError** at `update_Nowcast2.py:68`; (b) **2017-04-28 = GDP-release week** (BEA Q1 advance lands → target observed) → NO-FORECAST branch, which has a **latent shape bug** (`t_fcst` is a 1-elem array, so `y_old[0,i] = X_sm[t_fcst, v_news[i]]` assigns a (1,)-array into a scalar slot) → **ValueError** at `update_Nowcast.py:170`, NOT None-None. So v1's "GDP observed" branch never actually works. **Validated against v1's actual `nowcast_Q/nowcast_2017_q1.csv`: identical 18 vintages, `y_new`/`y_old` match to 1.7e-14.** Each golden row records `vintage_old` so the (non-contiguous) pairing is unambiguous for the 3b parity tests.

**✅ Phase 3b A4 + B1–B6 DONE (2026-06-02) — all pushed to `origin/refactor/v2` (tip `1b3bec2`).** Each step TDD (failing test → port → golden/parity → `just ci` green), incremental with confirm-before-fan-out:
- **A4** committed RESUME (`5d47401`) + pushed the 6 local 3a commits.
- **B1** `1ff07e8` `dfm_spec.py` (port of load_spec): `Model==1` filter (28 series), Blocks-aware, PascalCase property aliases so verbatim-ported bodies work.
- **B2** `38aa41f` `transform.py` (port of load_data): `+366` removed (Time = real `DatetimeIndex`), `np.isin`, ValueErrors raised, dead `lin:x*2` dropped. **Parity atol=0** vs v1. Added root `conftest.py` + mypy `Functions.*` skip-imports override.
- **B3** `52053cb` `_dfm_support.py` (port of remNaNs_spline → `rem_nans_spline`): all 5 methods. **Parity atol=0** (methods 2&3, the ones dfm uses). Did NOT port `decompose_common_factor` (no importers; B6 supersedes).
- **B4** `c7be0d9` `dfm.py` (de-MATLAB port of the 1086-line EM/Kalman core): fixed the `em_converged` `print().format()` bug + deleted the duplicate `max_iter=5000`; kept the A0 `.item()` shims; gated prints behind `verbose`. **Golden parity `1e-6`** (C/A/Q/R/Z_0/V_0/Mx/Wx + loglik + x_sm GDP tail). **1st review** → no numerical divergence, comment clarity in `88b0836`.
- **B5** `642b1e8` `news.py` (de-MATLAB port of update_Nowcast2/update_Nowcast): `update_nowcast(...)` + `News_DFM`/`para_const` verbatim; `+366` removed (MonthBegin horizon). **Nowcast golden parity `1e-6` over 18 vintages** (marked `slow`). Like v1, raises on the 3 no-forecast vintages (B7 replicates the skip).
- **B6** `e712745` `decomposition.py` (NEW logic): `gdp_common_share` replaces `extract_common_residual` (which hardcoded `gdp_resid=0.0` → `share≡1`). Returns the honest **one-step projection residual** `observed − C·f`. **Fixed two latent bugs** in BOTH v1 and the plan's literal snippet (to match the plan's documented intent): (1) **standardise with `Mx/Wx` before `SKF`** (Kalman runs in standardised space); (2) evaluate at the latest **observed** GDP period (last monthly row is NaN). → `share_common ≈ 0.598`. **2nd review** (range `88b0836..e712745`): *With fixes*, no Critical; B5 a faithful port, B6 deviations confirmed correct empirically (prior `Zm`→0.598 vs posterior `ZmU`→0.99992). Important fix in `1b3bec2`: pinned the test to `approx(0.598, abs=0.01)` (the loose `!=1.0` let the posterior degeneracy through).

**✅ B7 + B8 DONE (2026-06-03) — Phase 3 baseline-2017q1 COMPLETE (committed LOCAL; push gated on the final sweep review).**
- **B7** `06363f0` `src/gdpnowcast/nowcast/{__init__,config,runner}.py` (`run_quarter`) + `tests/test_runner_golden.py`. Re-estimates prev/curr params from data vintages (v1's opaque pickles + broken absolute Windows paths gone), walks the 21 contiguous pairs, **skips the same 3** vintages → **18 rows, golden parity `1e-6`** (`y_old`/`y_new`); the test also asserts the skipped set == `GOLDEN["skipped"]`. **Two deliberate choices over the plan skeleton:** the skeleton OMITTED the `try/except` (would crash on the first no-news pair) → added it but **narrowed to the two VERIFIED exception types** (`TypeError` no-news None-None; `ValueError` GDP-release NO-FORECAST shape bug) instead of v1's blanket `except Exception`, so an unexpected error surfaces; skipped vintages recorded on `df.attrs["skipped"]` (not v1's silent print). Identical 18-row output.
- **B8** added the `just test-golden` recipe. ⚠️ Plan/earlier-note said `-m "golden or slow"`, but the goldens are marked BOTH `golden` and `slow`, so `golden or slow ≡ slow` ≡ the existing `test-slow` (which also pulls the 3 network ALFRED tests). Corrected recipe = `-m "golden or slow" --ignore=tests/test_fetch_integration.py` → exactly the **4 local heavy tests** (3 goldens + B6 decomposition), no network. **mypy was already clean on all 17 src files** (helpers typed in B4/B5) → B8 typing was a no-op. `just ci` green; `just test-golden` green.
- **Still OPEN (Phase 4):** fiscal variant + remaining `CONFIG_*` quarters (full multi-quarter backtest); `pca(GDPC1)` BEA-growth regression test; and the **Phase 4.0 gate** (🔵 block) BEFORE any headline rerun.
- Parity runs on `data/US_new_v1` (v1 panel) to isolate port-correctness from the Phase-2 data-panel difference (a Phase-4 decision).

---

## 🔵 NEW (2026-06-03): Phase 4.0 — evaluation-methodology GATE (decided, NOT yet executed)

A long design discussion (the release-week nowcast vs the BEA advance) produced a firm sequencing decision: **before** Phase 4's headline 2017-2025 backtest + RMSE/MAE table, run a single **evaluation-methodology gate**. Every item below changes *what the headline backtest runs on*, so doing any of them AFTER the headline = redoing the headline + the 4.5 benchmarks + the 5 dashboard, and splitting the §6 model-comparison table across two calendars. So this is a front-of-Phase-4 gate, **never later**. B7/B8 stay a faithful v1 port (they do NONE of this).

1. **Target masking — MANDATORY (correctness).** On the current-quarter, set the GDP target cell → `NaN` before the smoother, so the release-week vintage produces a *genuine forecast* (drives `News_DFM` into the FORECAST branch) instead of (i) reading back the just-released advance (error ≈ 0, verified `0.694` vs `0.7`) or (ii) crashing on the shape bug. Cheap, in-memory, **no re-fetch**. Implemented as a runner **mode** ON TOP of the B7 faithful port (masking deviates from the v1 golden → it cannot live inside B7's parity test). This *is* the red-team **rank-12 "real-time-leak test"** (still un-phased in the design doc).
2. **Vintage calendar Thursday vs Friday — NOW-OR-NEVER.** Expensive (regenerate the manifest + re-fetch ALFRED 2017-2025). Either adopt at the gate or keep **Friday + masking permanently** — deferring past the headline = rework. Thursday lands the final nowcast "just before" the typical BEA advance day; it is **second-order** vs masking. NB our manifest is **extracted from v1's real files**, not a `W-FRI` generator, so this is a full calendar regeneration, not a weekday swap.
3. **Data panel truncate-vs-fuller** — the already-open ⚑ Phase-3 input decision; same "what panel does the headline run on" question, belongs in the same gate.
4. **Headline metric = "final nowcast vs advance"** as the primary backtest metric (NY-Fed style).

**Facts verified this session (sources logged in chat):** BEA advance = **8:30 a.m. ET** (morning, not afternoon), release **day varies** (Q1-2017 = Fri Apr 28 per our own data; Q1-2026 = Thu Apr 30); NY Fed publishes Fri 11:15, data-cutoff 10:00 → it **keeps same-day non-GDP data and excludes only the target = masking semantics**, not a timing trick; **ALFRED granularity is daily** (`realtime_start` is a date) so intraday morning/afternoon is **unreconstructable** → any "timing" approach can only be a *day-shift*, which also drops same-day non-GDP data (less faithful than masking). Conclusion: **masking is the recommendation**; Thursday is an optional, now-or-never refinement.

---

## 🔴 NEW (2026-05-30): red-team backlog — READ BEFORE EXECUTING

A 64-agent workflow (`v2-improvement-redteam`) red-teamed the **go-forward** plan (not v1), reading all prior audit/verification reports as input. Output: **`docs/audit/v2-improvement-backlog.md`** (28 prioritized items, 42 findings raised / 37 survived / 5 refuted). **Read it before executing Phase 1.**

**5 critical blockers (would stop the MVP backtest from running at all):**
1. **`fridays_between()` drops the 33 quarter-start vintages** the DFM re-estimates params on → Phase 4 can't reproduce `Results.pdf`. Fix the vintage list + change Phase 2 exit criterion to a superset assertion (≥485 filenames, all present). *(Phase 2/4)*
2. **Phase 2 is mis-scoped:** there is **no v1 fetcher for 32 of 35 series** (`variables_creation.py` only patches the 3 fiscal ones). Re-scope as *building* a new ALFRED fetcher, re-budget 4-6 d, add a pre-Phase-2 go/no-go ALFRED-coverage spike. *(Phase 2)*
3. **Golden baseline must be frozen from UNMODIFIED v1 before de-MATLAB.** Split Phase 3 → 3a (freeze, commit `golden/` + SHA) / 3b (refactor), hard gate between. *(Phase 3)*
4. **Headline "non-redundant but not significant" is an underpowered failure-to-reject** (T≈10-30) with zero power/MDE analysis. Make sample size THE framing device (MDE / equivalence / TOST). *(Phase 4/6/8)*
5. **Phase 7a "COVID factor + outlier vector" is severed from the SV/Bayesian machinery that identifies it** (the plan excludes both). Re-spec as an identifiable outlier/dummy device with identification-aware exit criteria. *(Phase 7a, partial)*

**Nearly-free high-leverage sequencing fixes:** move the backtest runner Phase 5 → Phase 3 so Phase 4's re-run is executable (rank 4); don't deploy the public Streamlit MVP with no GDPNow/ARMA benchmark — pull benchmarks forward or unlist (rank 7); commit recovered `update_Nowcast.py` in Phase 1 so the repo runs on clone (rank 24).

**Notable refutations (verification protected the plan):** the "DM loss-differential sign mixup" and "must add HAC" findings were both **refuted** — verifiers checked Appendix C + code and confirmed the plan's quarterly-HLN approach is correct and HAC is a ~no-op at h=1. Don't re-open those.

---

## What this is

A complete revision (v2) of the master thesis project `GDPnowcast-fiscal`. Goal: research-grade re-do targeting **portfolio piece first, working paper second**. Triggered by a 3-agent audit on 2026-05-11 that found:

- DFM core is **correct** (faithful port of FRBNY Banbura-Modugno DFM)
- ~85% of root-level Python is **near-duplicate** (18 nowcast scripts, 2 dashboards)
- **Four candidate methodology bugs.** Verification (2026-05-11) outcome: 2 confirmed (MTSDS133FMS un-deseasonalised; DM at weekly granularity, plus stacked bug: plain `ttest_1samp` despite Appendix C claiming HAC), 1 partially confirmed (W875RX1 mislabel yes, redundancy refuted on `pch`), 1 refuted (GCEC1 shift is the fix, not the bug). See `docs/audit/v1-verified/00_synthesis.md`.
- `Functions/update_Nowcast.py` is **missing from HEAD** but **recoverable from git** (`git show 729b40b:Functions/update_Nowcast.py`, 431 lines, accidentally deleted in `e0928d5`).
- FRED API key committed in plaintext (burned — to rotate in Phase 1 Task 3).

---

## What's already done

- [x] Repo cloned locally to `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal`
- [x] Branch `refactor/v2` created (not yet pushed)
- [x] 3-agent audit complete — reports in `docs/audit/v1/`:
  - `00_synthesis.md` — unified synthesis (READ FIRST)
  - `01_structure_audit.md` — folder structure + reproducibility
  - `02_code_quality_audit.md` — Python code quality
  - `03_methodology_audit.md` — statistical/econometric correctness
- [x] Brainstorming complete (scope, end-goal, data strategy, phasing, structure, stack, methodology)
- [x] Design doc written: `docs/plans/2026-05-11-v2-design.md` (READ SECOND)
- [x] **Audit findings verified (2026-05-11)** — 5 parallel agents, reports in `docs/audit/v1-verified/`:
  - `00_synthesis.md` — **READ THIRD** — consolidated outcomes + impacts on the design doc
  - Bug #1 (GCEC1 shift): **REFUTED** — the shift is the fix, not the bug
  - Bug #2 (MTSDS133FMS `lin`): CONFIRMED (April = +1.13σ; `ch1` shrinks to 0.12σ)
  - Bug #3 (DM weekly): CONFIRMED + **stacked bug** — code uses plain `ttest_1samp`, no HAC, despite Appendix C claiming HAC
  - Bug #4 (W875RX1): **PARTIALLY** — mislabel yes; redundancy refuted on `pch` (r=0.09). Decision: keep as-is.
  - Reproducibility: CONFIRMED + `update_Nowcast.py` **recoverable from git `729b40b`**
- [x] **Design doc revised + reviewed (2026-05-11)** — reviewer agent found 4 Critical + 3 Important contradictions left over from the pre-verification draft; all fixed in `docs/plans/2026-05-11-v2-design.md`. Review report at `docs/audit/v1-verified/06_design_doc_review.md`.
- [x] **Phase 1 implementation plan written + reviewed + fixed (2026-05-11)** — at `docs/plans/2026-05-11-phase1-implementation.md`. 13 tasks. Reviewer agent (`docs/audit/v1-verified/07_phase1_plan_review.md`) found 2 Critical bugs (indentation in the FRED-key patch; incomplete grep filter in exit criterion E) and 1 wording issue — all three fixed.
- [x] **Go-forward plan red-team (2026-05-30)** — 64-agent workflow `v2-improvement-redteam`. 42 findings raised / 37 survived / 5 refuted → **`docs/audit/v2-improvement-backlog.md`** (28 prioritized items). Found 5 critical blockers the v1 audit missed (see the 🔴 section near the top of this file). Backlog + RESUME committed in `87ae1ef`.
- [x] **Backlog triaged + docs revised (2026-05-31)** — 5 critical + 3 sequencing accepted; folded into the design doc + Phase 1 plan; roadmap re-budgeted to ~14-21 d for the portfolio MVP.
- [x] **Phase 1 (Foundation) executed + pushed (2026-05-31)** — src-layout skeleton + `uv`/`ruff`/`mypy`/`pytest`/`pre-commit`/`just`/CI tooling + `.gitignore` + data untracked + FRED-key patch + `.env.example` + README (badge/confidence) + `update_Nowcast.py` recovered. `just ci` green. Plan: `docs/plans/2026-05-11-phase1-implementation.md`.

---

## What's next (in order)

### Immediate — ✅ triage + revision + Phase 1 all DONE 2026-05-31:

1. ✅ **Backlog triaged** — 5 critical (ranks 1-3, 5, 6) + 3 sequencing (ranks 4, 7, 24) accepted; COVID re-spec'd as an identifiable outlier/dummy (rank 6); benchmarks pulled into a new **Phase 4.5** (rank 7). Deferred to a later pass: ranks 9-12 + medium polish 13-28.
2. ✅ **Docs revised** — folded into `docs/plans/2026-05-11-v2-design.md` (Phase 2 fetcher re-scoped 4-6 d; Phase 3 → 3a/3b; runner → Phase 3; Phase 7a COVID re-spec; power/MDE narrative; budget 14-21 d) and the Phase 1 plan (rank 24 + execution deviations).
3. ✅ **Phase 1 executed + pushed** — inline on `refactor/v2`, `just ci` green. Tooling installed this machine: `uv` 0.11.17, `just` 1.51.0.

**▶ Phase 2 plan written + Tasks 1-8 executed (2026-06-01)** — see the ✅/⏳ blocks near the top. Plan at `docs/plans/2026-06-01-phase2-implementation.md`. Only the gated **Task 9** (full fetch) remains. The constraints below were baked into the build and are kept here as the design record:
- **Forward-looking-bias guardrail (Matteo's standing concern):** strict point-in-time `realtime_start=realtime_end=D`; never ffill/interpolate/backfill an empty as-of cell (leave NaN); truncate observations to `<= D`; ship a leakage test. See napkin Domain #4.
- **Vintage manifest must include the 33 quarter-start re-estimation vintages**, not Fridays-only (`fridays_between` in `variables_creation.py` drops them).
- **Phase 2 exit = superset assertion** (≥485 filenames, all present) — not a 5-random sample.
- All 35 series GO ⇒ no fallback branch needed.
- Quarterly handling for the 4 q-series (`GDPC1`, `ULCNFB`, `A261RX1Q020SBEA`, `GCEC1`); preserve the v1 "last-month-of-quarter" stamping convention (napkin Domain #1).
- Use `load_dotenv(override=True)` in `get_fred()` (napkin Tooling #3).
- **Before the LARGE fetch** (not the spike): get `.venv`/`data/` out of OneDrive sync.

### Design-doc decisions captured 2026-05-11 (post-verification):
- Bug #1 (GCEC1 shift) — **dropped from Phase 4.** Replaced by a unit test on `pca(GDPC1)` vs BEA growth.
- Bug #4 (W875RX1) — **left as-is in spec.** No category rename, no drop. The taxonomic mislabel debate is parked.
- Bug #3 (DM) — **Quarterly + HLN only.** HAC implementation is out of scope (v1 code never had it).
- Phase 3 — `update_Nowcast.py` **recovered from git `729b40b`**, not re-derived from upstream.

### Phase roadmap (from design doc §3):

| # | Phase | ETA |
|---|---|---|
| 1 | Foundation (skeleton + tooling + FRED key rotation) | 1-2 d |
| 2 | Data pipeline (FRED/ALFRED rebuild) | 2-3 d |
| 3 | Library migration + tests (de-MATLAB, fix v1 bugs) | 3-4 d |
| 4 | **Methodology fixes** (the 4 bugs from the audit) | 2-3 d |
| 5 | Portfolio polish (1 CLI, 1 dashboard, deploy) | 2-3 d |
| — | **Portfolio MVP complete** | |
| 6 | Validation rigor (benchmarks, encompassing, holdout, intervals) | 3-4 d |
| 7a | Staff Nowcast 2.0: COVID factor | 1-2 d |
| 7b | Staff Nowcast 2.0: long-run trend (optional) | 2-3 d |
| 8 | Paper writing | 5-7 d |

---

## How to resume from a fresh Claude session

In PyCharm terminal, from this repo root:

```bash
claude
```

Then say something like:

> "I'm resuming the GDPnowcast-fiscal v2 refactor. Read RESUME.md (especially the 🔴 red-team section at the top) and `docs/audit/v2-improvement-backlog.md`. Before executing Phase 1 we need to triage the backlog and revise the design doc + Phase 1 plan to fold in the 5 critical blockers. Let's start by triaging the confirmed/high items together, then revise the plan, then execute."

Claude will pick up from there. Do NOT skip the design-doc, verification, and red-team-backlog reading — they explain why specific tasks exist and what must change before execution.

**Current branch tip:** `refactor/v2` — B1–B6 pushed (`1b3bec2`); **3 local commits ahead, NOT pushed** (`bb0ce9d` Phase-4.0 gate + skip-mechanism doc fix, `06363f0` B7 runner, + the B8 commit this file is part of) — push gated on the final sweep review. Phase 2 → Phase 3 plan (`4eafca2`) → Phase 3a (6 commits `28161cc`…`1014118`) → A4 RESUME (`5d47401`) → Phase 3b B1–B6 (`1ff07e8` `38aa41f` `52053cb` `c7be0d9` `88b0836` `642b1e8` `e712745` `1b3bec2`) → gate/docs `bb0ce9d` → B7 `06363f0`. `main` untouched at `d50a2bc`, **never merged into** (hard rule). `data/` holds fetched vintages (`US_new`/`US_fiscal` 486 each) + v1 backups (`US_new_v1` 486, `US_fiscal_v1` 485) — all gitignored.

**⏸ PAUSED 2026-06-03 — Phase 3 baseline-2017q1 COMPLETE; final sweep review pending before push.** B1–B6 are pushed (`1b3bec2`); `bb0ce9d` (gate/docs) + `06363f0` (B7) + the B8 commit are **LOCAL, not pushed** — the agreed review cadence runs a **final sweep checkpoint review** (subagent, B7→B8 range) BEFORE pushing. Next session, in order: (1) run the final sweep review + address any findings; (2) `git push origin refactor/v2`; (3) begin the **Phase 4.0 evaluation-methodology gate** (🔵 block at the top: target masking [mandatory] + Thu-vs-Fri calendar [now-or-never] + data-panel truncate-vs-fuller + headline metric) — do NOT start Phase-4 body work until the gate is resolved. To resume, run `claude` and say: *"Riprendo il refactor v2 — Phase 3 baseline è completo e committato local; leggi RESUME.md, facciamo il final sweep review di B7/B8, poi push."*

---

## Decisions already locked (from brainstorming)

- **Scope:** Re-do completo, research-grade.
- **End goal:** Portfolio first, paper second.
- **Data:** Gitignored + rebuild from FRED/ALFRED via `gdpnowcast fetch`. Excel format preserved.
- **Stack:** Python 3.13, `uv` (conda fallback), Typer CLI, Streamlit dashboard, pytest, ruff, mypy non-strict, GitHub Actions, `justfile`.
- **Structure:** `src/gdpnowcast/` layout. `dfm.py` single file (split deferred). No `scripts/` dir — CLI via Typer.
- **Methodology Phase 4 (revised post-verification):** Two fixes shipped (MTSDS133FMS → `ch1` (fallback X-13); quarterly final-week DM with HLN small-sample correction, rewrite in `src/gdpnowcast/analysis/diebold_mariano.py`) + one regression test (`pca(GDPC1)` vs BEA-published Q-over-Q growth). Bug #1 (GCEC1 shift) and Bug #4 (W875RX1) dropped from Phase 4 scope. HAC variance deliberately out of scope (v1 never had it; matching Appendix C is a separate scope expansion).
- **Methodology Phase 6:** GDPNow + ARMA + encompassing + holdout (2017-22 train / 2023-25 test) + predictive intervals. SPF best-effort.
- **Methodology Phase 7:** COVID factor mandatory (Phase 7a), long-run trend optional (Phase 7b). Bayesian/TVP excluded.
- **Final comparison:** **6 models** — v1, fixed-no-fiscal, fixed-with-fiscal (3 fiscal vars kept), +COVID factor, GDPNow, ARMA.

---

## Important caveats

1. **`Results.pdf` numbers are reproducible *with* the recovered `update_Nowcast.py`** (`git show 729b40b:Functions/update_Nowcast.py > Functions/update_Nowcast.py`). At HEAD of the public repo the pipeline is broken — that's a fixable on-clone gap, not a permanent loss.
2. **Phase 4 fixes will likely collapse the "Q2 and post-2020 fiscal effect" headline.** The verification confirms April is +1.13σ on raw `lin` and `ch1` shrinks it to 0.12σ; the DM significance also collapses (6.4 → ~1.46 borderline). Honest narrative shift expected: from "fiscal significantly improves nowcasting" → "fiscal carries non-redundant transfer-cleaned income signal but is not significant at conventional thresholds".
3. **FRED API key in v1 is burned.** Rotation is Task 3 of the Phase 1 plan (manual browser step at fred.stlouisfed.org).
4. **Dashboard deploy** can't do live FRED fetches on Streamlit Cloud (ephemeral disk, secrets management). The Phase 5 design reads from pre-computed `docs/dashboard_data/`.
