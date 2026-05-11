# RESUME — where we left off

**Last touched:** 2026-05-11
**Branch:** `refactor/v2` (off main `d50a2bc`)
**Status:** Design approved. Pending audit-verification, then implementation plans phase by phase.

---

## What this is

A complete revision (v2) of the master thesis project `GDPnowcast-fiscal`. Goal: research-grade re-do targeting **portfolio piece first, working paper second**. Triggered by a 3-agent audit on 2026-05-11 that found:

- DFM core is **correct** (faithful port of FRBNY Banbura-Modugno DFM)
- ~85% of root-level Python is **near-duplicate** (18 nowcast scripts, 2 dashboards)
- **3-4 methodology bugs** likely inflate the headline result (GCEC1 misalignment, MTSDS133FMS un-deseasonalised, DM at weekly granularity, W875RX1 mis-labelled fiscal)
- `Functions/update_Nowcast.py` is **missing** from the repo → pipeline broken on clean clone → Results.pdf not reproducible
- FRED API key committed in plaintext (already burned)

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

---

## What's next (in order)

### Immediate (next session, do these in this order):

1. **Read** `docs/plans/2026-05-11-v2-design.md` end-to-end. Approve or request changes.
2. **Verify audit findings** — dispatch agents to verify the 4 methodology bugs and 2 reproducibility blockers are real before scheduling fixes. Output reports go to `docs/audit/v1-verified/`. (Per Matteo's explicit instruction.)
3. **Write Phase 1 implementation plan** — `docs/plans/2026-05-12-phase1-implementation.md`. Use the `superpowers:writing-plans` skill.
4. **Execute Phase 1** (Foundation: skeleton + tooling).

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

> "I'm resuming the GDPnowcast-fiscal v2 refactor. Read RESUME.md and docs/plans/2026-05-11-v2-design.md, then proceed with the verification of audit findings (step 2 in RESUME.md). Dispatch agents to verify the methodology bugs in docs/audit/v1/03_methodology_audit.md sections 'Methodology correctness' and 'Validation design issues', and the broken-import + leaked-API-key findings."

Claude will pick up from there. Do NOT skip the verification step — it's a deliberate gate before scheduling fixes.

---

## Decisions already locked (from brainstorming)

- **Scope:** Re-do completo, research-grade.
- **End goal:** Portfolio first, paper second.
- **Data:** Gitignored + rebuild from FRED/ALFRED via `gdpnowcast fetch`. Excel format preserved.
- **Stack:** Python 3.13, `uv` (conda fallback), Typer CLI, Streamlit dashboard, pytest, ruff, mypy non-strict, GitHub Actions, `justfile`.
- **Structure:** `src/gdpnowcast/` layout. `dfm.py` single file (split deferred). No `scripts/` dir — CLI via Typer.
- **Methodology Phase 4:** All 4 bugs fixed. MTSDS133FMS → `ch1` (fallback X-13). DM at quarterly level with HLN. W875RX1 dropped honestly.
- **Methodology Phase 6:** GDPNow + ARMA + encompassing + holdout (2017-22 train / 2023-25 test) + predictive intervals. SPF best-effort.
- **Methodology Phase 7:** COVID factor mandatory (Phase 7a), long-run trend optional (Phase 7b). Bayesian/TVP excluded.
- **Final comparison:** 5 models — v1, fixed-no-fiscal, fixed-with-fiscal, +COVID factor, GDPNow, ARMA.

---

## Important caveats

1. **`Results.pdf` numbers are NOT reproducible** from the public v1 repo (missing `Functions/update_Nowcast.py`). Verify locally if you have a backup before proceeding.
2. **Phase 4 fixes may collapse the headline finding.** "Fiscal helps Q2 and post-2020" is likely partly a calendar artefact. This is an honest-research feature, not a bug — but be prepared for the narrative to shift.
3. **FRED API key in v1 is burned.** Rotate at start of Phase 1.
4. **Dashboard deploy** can't do live FRED fetches on Streamlit Cloud (ephemeral disk, secrets management). The Phase 5 design reads from pre-computed `docs/dashboard_data/`.
