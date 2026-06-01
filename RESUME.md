# RESUME — where we left off

**Last touched:** 2026-06-01 (**Phase 2 COMPLETE** — full fetch run, ~972 vintages built, exact v1 match verified across 11.3M cells, all gates green)
**Branch:** `refactor/v2` (off main `d50a2bc`). ⛔ **NEVER merge into `main`** — v2 lives permanently on this branch (Matteo's hard rule).
**Status:** ✅ **Phase 1 (Foundation) complete and pushed.** On 2026-05-31 the red-team backlog was triaged (5 critical + 3 sequencing accepted), folded into the design doc + Phase 1 plan, then Phase 1 was executed inline: src-layout skeleton, `uv`/`ruff`/`mypy`/`pytest`/`pre-commit`/`just`/GitHub-Actions tooling, `.gitignore`, data untracked (1300→54 tracked files, 1.65 MB), FRED-key fallback patched + `.env.example`, README (confidence-framed + CI badge), `update_Nowcast.py` recovered from git. `just ci` green (lint + mypy + 2 smoke tests). Three environment deviations applied (justfile `windows-shell`, CI uv `0.11.x`, pyproject `[tool.uv] link-mode = "copy"` for OneDrive) — see the Phase 1 plan's "Executed 2026-05-31" note.

**✅ FRED key rotated (2026-06-01).** New key generated on the existing FRED account, stored in local `.env` only, and confirmed working (`get_series_info("GDPC1")` → OK). Gotcha for next time: a stale `FRED_API_KEY` Windows **User** env var (`3b80…`) shadowed `.env` because `load_dotenv` doesn't override existing env vars — fixed by removing the User var + using `load_dotenv(override=True)` in data-layer loaders. See napkin Tooling #3.

**✅ Pre-Phase-2 ALFRED-coverage spike PASSED (2026-06-01) — GO 35/35.** `tools/alfred_coverage_spike.py` confirmed all 35 series (32 baseline + 3 fiscal) resolve on FRED, return a non-empty point-in-time as-of series, and have ALFRED vintage history back well before 2016-12-09 (tightest = `MTSDS133FMS` earliest 2015-09-11). **No fallback branch needed** — every series rebuilds directly from ALFRED point-in-time; the design doc §8 risk "some series may lack vintages back to 2016-12" did not materialize.

**⚠️ Environment caveat:** `.venv` (and the repo) sit inside OneDrive, which locks venv files during `uv` reinstalls. Recommend excluding the repo (or at least `.venv`/`data/`) from OneDrive sync before Phase 2's large fetch.

**✅ Phase 2 data layer BUILT + committed (2026-06-01).** New 35-series ALFRED point-in-time fetcher implemented and committed on `refactor/v2` (Tasks 1-8 of `docs/plans/2026-06-01-phase2-implementation.md`): `src/gdpnowcast/data/{spec,vintages,fred,builder}.py` + `gdpnowcast fetch` (CLI) + committed manifests (`configs/vintages_{baseline,fiscal}.csv`, 486 each) + 19 offline tests + 12 network no-leakage cross-validation tests (`reconstruct_asof` vs point-in-time API, `rtol=0/atol=0`) + `docs/data_sources.md` + 3 tools (coverage spike, manifest generator, v1 diagnostic). `just ci` green (19 passed, 2 superset SKIPPED pending fetch, 12 slow deselected). **Two collateral bugs found + fixed while committing:** (a) `.gitignore`'s unanchored `data/` was silently ignoring the whole `src/gdpnowcast/data/` package → anchored to `/data/`; (b) an accidental `.env.example`→`.env` find-replace had corrupted `.env.example`, `variables_creation.py`, `README.md`, and the Phase 1 plan → all reverted.

**✅ Task 9 DONE (2026-06-01) — Phase 2 COMPLETE.** Ran the full fetch: backed up v1 dirs (`data/US_new_v1` 486, `data/US_fiscal_v1` 485), then `gdpnowcast fetch --variant baseline` (486 files) + `--variant fiscal` (486 files) — both built cleanly into `data/US_new` / `data/US_fiscal` (gitignored). Exit verification all green:
- **Superset gate PASSED** for both variants (`tests/test_superset.py`): generated ⊇ manifest.
- **Value match EXACT vs v1:** `tools/compare_to_v1.py` over **all** vintages = **0 difference across 11.3M cells** (baseline 5,428,161 + fiscal 5,906,348; global max abs delta 0, no diverging series). The 32 baseline series — which v1 sourced from the FRBNY pipeline, not its own fetcher — reproduce bit-for-bit, so they too were ALFRED point-in-time underneath. Documented in `docs/data_sources.md`.
- **Only structural diff (cosmetic):** 4 early vintages (`2016-10-03`, `2016-12-02`, `2016-12-07`, `2017-02-03`) carry one extra trailing **all-NaN** month (the vintage's own month, no data published yet) that v1 trimmed. No value differs, not look-ahead (it's the vintage month, and it's empty).
- **`just ci` green:** 21 passed (incl. both superset tests), 12 slow deselected, ruff + mypy clean.

**▶ NEXT: Phase 3** (library migration + tests: de-MATLAB, fix v1 bugs; split 3a freeze golden / 3b refactor; move backtest runner into Phase 3). The data layer is done and verified — Phase 3 consumes `data/US_new` / `data/US_fiscal`.

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

**Current branch tip:** `refactor/v2` — Phase 2 committed + **pushed** to `origin/refactor/v2` (8 commits 2026-06-01: gitignore anchor → data layer → ruff config → CLI → tests → tooling → docs → CI/RESUME), plus a Task-9 wrap-up commit (`data_sources.md` + RESUME). `main` untouched at `d50a2bc`, never merged into. `data/` now holds the freshly-fetched vintages (`US_new` 486, `US_fiscal` 486) + v1 backups (`US_new_v1` 486, `US_fiscal_v1` 485) — all gitignored, never committed. Working tree clean except `.claude/` (deliberately untracked). Next action = **Phase 3**.

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
