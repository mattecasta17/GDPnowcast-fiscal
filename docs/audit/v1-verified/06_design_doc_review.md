# Design doc review — 2026-05-11-v2-design.md

**Reviewer:** Subagent dispatched 2026-05-11
**Document SHA:** (skip — uncommitted)
**Verdict:** NEEDS REVISION

The §6 Phase 4 table was correctly revised, but the §3 phasing table, §7 exit
criteria, and §6 model-comparison table were not synchronised. Two of those are
direct contradictions that would mislead anyone executing Phase 4. Phase 1 is
not blocked — the inconsistencies live downstream — but they must be fixed
before the Phase 4 implementation plan is written.

---

## Critical findings

### C1. §3 Phase 4 row is stale and contradicts §6 Phase 4

`docs/plans/2026-05-11-v2-design.md:56`:

> "**4** | **Methodology fixes** | Fix GCEC1 shift, MTSDS133FMS → `ch1`, DM at
> quarterly level with HLN small-sample correction, **W875RX1 dropped
> honestly**. Re-run full backtest; publish new RMSE/MAE numbers | 2-3 d"

This contradicts both §6 (`:228-229`) which explicitly DROPS Bug #1 (GCEC1
shift) and DROPS Bug #4 (W875RX1) from Phase 4, and `RESUME.md:50-51` which
records the same decision. **Severity: critical** — the design's headline
phasing table tells a future executor to do exactly the two things §6 says
not to do.

Recommended fix: rewrite the Phase 4 row to enumerate "MTSDS133FMS → `ch1`,
quarterly DM + HLN, BEA-growth regression test on `pca(GDPC1)`".

### C2. §7 Phase 4 exit criterion still says "Four methodology bugs fixed"

`docs/plans/2026-05-11-v2-design.md:274`:

> "4 | **Four methodology bugs fixed in code.** Full backtest rerun on
> 2017-2025. New RMSE/MAE table published in `docs/results.md`. Comparison vs
> v1 numbers documented"

Per the revised §6, Phase 4 ships **two bug fixes plus one regression test**,
not four bug fixes. `00_synthesis.md:22` records the actual count:
"3 confirmed as-stated, 1 confirmed + extra bug, 1 partially confirmed, 1
refuted" — and §6 explicitly de-scoped HAC, Bug #1, and Bug #4. **Severity:
critical** — this exit criterion is now unsatisfiable as written.

Recommended fix: change to "Two methodology fixes shipped (MTSDS133FMS `ch1`,
quarterly DM + HLN), `pca(GDPC1)` BEA-growth regression test green, full
backtest rerun…".

### C3. §6 Final model comparison table is internally inconsistent with §6 Phase 4 decision

`docs/plans/2026-05-11-v2-design.md:260`:

> "| Fixed legacy DFM (with fiscal) | After Phase 4 fixes, with **2 fiscal vars
> (W875RX1 dropped)** |"

§6 Phase 4 (lines 229) explicitly says W875RX1 **stays in the spec as-is**.
The model-comparison table at line 260 says it is dropped. **Severity:
critical** — same document, two opposite claims about whether the fiscal
variant has 2 or 3 fiscal vars in the headline comparison.

Recommended fix: change the "2 fiscal vars (W875RX1 dropped)" parenthetical
to "3 fiscal vars" or simply remove the parenthetical.

### C4. §8 exit criterion references "5-model comparison table" but §6 lists six rows

`docs/plans/2026-05-11-v2-design.md:278`:

> "8 | Paper PDF builds via `just paper`. **5-model comparison table** in
> main text…"

§6 `:256-263` lists six models in the final comparison: Thesis v1, Fixed
legacy no-fiscal, Fixed legacy with-fiscal, +COVID factor, GDPNow, ARMA(1,1).
`RESUME.md:98` also describes "5 models — v1, fixed-no-fiscal,
fixed-with-fiscal, +COVID factor, GDPNow, ARMA" — which is six items
mis-labelled as five. **Severity: critical (consistency)** — the discrepancy
predates the 2026-05-11 edits but is now exposed by the verification scope
change.

Recommended fix: pick a number. "Six-model comparison" is the simplest.

---

## Important findings

### I1. §1 Context still presents the four-bug framing as fact

`docs/plans/2026-05-11-v2-design.md:16-20` lists all four bugs without any
"likely / before verification" hedging:

> "**3-4 methodology bugs** likely inflate the headline result… 1. GCEC1
> mis-aligned… 4. W875RX1 mis-labelled as 'fiscal' (it's personal income
> ex-transfers, **ρ=0.95 with DSPIC96 already in baseline**)"

The ρ=0.95 figure is on levels; verification confirmed the actual transform
`pch` yields r=0.09 (`05_w875rx1_redundancy.md`). §6 acknowledges the
correction, but §1 still reads as if the 0.95 redundancy claim stood. A
future reader (especially a paper reviewer) skimming §1 only will form the
wrong impression.

Recommended fix: append one sentence "(Bug #1 refuted post-verification; Bug
#4 partially refuted — see §6.)" to the bullet list, or change ρ=0.95 to
"ρ=0.95 on levels but r=0.09 on the `pch` transform actually used".

### I2. DSPIC96 mis-named "Personal Income" — not captured anywhere in the design

Verification raised this twice (`00_synthesis.md:73`,
`05_w875rx1_redundancy.md:37-40`): both specs label DSPIC96 as "Personal
Income" when it is "Real Disposable Personal Income". The user's decision
was to "leave W875RX1 alone" — but that decision does not implicitly cover
DSPIC96 (different series, different problem: just a label).

The design doc mentions neither the issue nor the explicit choice to defer.
This will be silently forgotten. **Severity: important** — a reader of the
paper looking at the spec will see "DSPIC96 — Personal Income" and may
challenge it.

Recommended fix: add one line in §6 Phase 4 ("DSPIC96 SeriesName in both
specs reads 'Personal Income'; correct to 'Real Disposable Personal Income'
as a cosmetic spec edit") or document the decision to defer in §8 open
questions.

### I3. "HAC out of scope" rationale is in §6 but not in §10 self-review

§6 line 234 correctly records "HAC kept out of scope" and gives the
rationale ("v1 code never had it; matching Appendix C is a separate scope
expansion"). But this is a notable scope decision that contradicts the
thesis's own Appendix C
(`04_dm_weekly_granularity.md:38-44`). A future
reader who only reads Appendix C and §10 self-review may re-introduce HAC
trying to "match the paper". §10 self-review at `:316-322` does not flag
this.

Recommended fix: add a bullet to §10: "Scope check: HAC variance is
deliberately out of scope for Phase 4 (rationale in §6); future maintainers
should not re-add it to 'match Appendix C' without re-opening scope."

### I4. §7 Phase 3 exit criterion enumerates "Three v1 bugs" — count is unverified but OK

`docs/plans/2026-05-11-v2-design.md:273`: "Three v1 bugs fixed (`dfm.py:786`,
unraised ValueErrors, broken `extract_common_residual`)". Spot-checking:

- `dfm.py:786` — confirmed: `print('...').format(...)` chained on a string
  literal (would `AttributeError` if the branch ever fires).
- `summarize.py:119` and `load_data.py:38, 148` — confirmed: bare
  `ValueError("...")` statements that construct an exception object but
  never `raise` it. So the "unraised ValueErrors" item is actually **at
  least 3 sites**, not 1 — counting them as one "bug" is a stylistic choice,
  fine, but make sure Phase 3 actually fixes all three locations.
- `extract_common_residual.py` "broken" — read the file (96 lines). It is
  not visibly syntactically broken; it depends on `Functions.dfm.SKF` and
  assumes `Spec.SeriesID` exists. Whatever "broken" means here is not
  obvious from the file alone. Phase 3 plan should pin down the precise
  failure mode before claiming a fix.

**Severity: important** — not blocking Phase 1, but the implementation plan
for Phase 3 should expand "broken `extract_common_residual.py`" with the
specific bug it fixes.

### I5. Phase 3 BEA-growth regression test — where does it live, Phase 3 or Phase 4?

§6 Phase 4 (`:235`) introduces "(new) `pca(GDPC1)` convention regression
test" as a Phase 4 item. §3 Phase 3 row (`:55`) does not mention it. §4
structure shows the test file `tests/test_transforms.py` with the comment
"CRITICAL: pca transform must match BEA published growth" (`:137`) but does
not say which phase implements it.

The transform-test scaffold belongs in Phase 3 (it tests the migrated
`transforms.py`); the test data and the assertion that BEA's published
numbers match within 0.05 pp belongs in Phase 4. The design conflates these.

**Severity: important** — Phase 3 implementation plan needs to know whether
the test fixture (BEA growth series) is in scope.

Recommended fix: split into "Phase 3 = scaffold + tautological test on
synthetic data; Phase 4 = real BEA-growth assertion", or move the whole
thing into Phase 3 and have Phase 4 only consume it.

---

## Minor findings

### M1. §1 reproducibility bullet says `Results.pdf` not reproducible — true but partial

`:22`: "Results.pdf numbers cannot be reproduced from the public repo." Per
verification, `update_Nowcast.py` is recoverable from this same repo's git
history (`729b40b`). So with `git show 729b40b:Functions/update_Nowcast.py
> Functions/update_Nowcast.py`, the public repo *is* reproducible — just
not at HEAD. Worth a parenthetical.

### M2. §1 still says "3-4 methodology bugs likely inflate the headline result"

After verification it is **two confirmed bugs + one partially confirmed +
one refuted**. The "3-4" hedge has been overtaken by evidence. Stale.

### M3. `MajesticKhan/Nowcasting-Python` — not present in the design at all

The review brief asked to search for this string. It does not appear
anywhere in the design (only the resolved risk row at `:292` mentions the
recovery via git, no fork mention). Clean — no action needed. Noting only
because the review brief flagged it.

### M4. Risk row at `:290` still says "the 'Q2 effect' was an artefact, headline collapses"

This is conservative-realistic and still true post-verification. The
adjacent risks are fine. Note: Bug #4 is explicitly NOT in Phase 4 anymore,
so the "headline collapses" risk is now driven by Bug #2 alone (Bug #3
demotes significance but does not change point estimates). Not a defect —
just sharpen if you re-edit.

### M5. §3 Phase 3 row de-MATLAB description: "break up `InitCond`/`EMstep` internally"

Plausible but unchecked. `dfm.py` is at line 1 in the codebase; size and
function structure not verified against the 800-line splitting threshold
mentioned at `:183`. Likely fine; flag for Phase 3 planning.

### M6. Effort estimate for Phase 4 still says "2-3 d"

Scope shrank from 4 bugs → 2 bugs + 1 regression test. The estimate is now
generous, not under-scoped. Fine to leave as a buffer for the BEA-growth
test fixture work; flag only because §10 self-review could mention it.

---

## Things checked and confirmed clean

- §4 target repo structure: no stale references to deleted Phase 4 fixes;
  the `analysis/diebold_mariano.py` path matches §6 line 234.
- News_DFM recovery: `git show 729b40b:Functions/update_Nowcast.py`
  produces a 431-line file with `def News_DFM` at line 122, `def
  update_nowcast` at line 10, `def para_const` at line 347 — matches the
  design's claim in `:55` and the resolved-risk row at `:292`.
- DM code location: `dashboard_nowcast_fiscal.py:1325` opens the "DIEBOLD–
  MARIANO TEST SECTION", `:1377-1379` defines `dm_test` as `ttest_1samp` —
  matches `:234`.
- `dfm.py:786` print-format bug: confirmed (`print('…').format(…)`).
- `load_data.py:38` and `:148`: confirmed (bare `ValueError("…")` not
  raised).
- `summarize.py:119`: confirmed (bare `ValueError`).
- §5 stack tooling — no methodology references, unaffected by
  verification, internally consistent.
- §8 risks "News_DFM recovery" marked Resolved with correct evidence.
- §8 open questions Q1 marked resolved with correct evidence.
- `MajesticKhan/Nowcasting-Python` appears nowhere in the design (the
  upstream-port contingency was already removed).
- "drop W875RX1" appears only at `:260` (model-comparison table) and `:56`
  (Phase 4 row) — both flagged in C1/C3 above. The §6 Phase 4 prose at
  `:229` is correctly updated.

---

## Recommendation

Matteo should make four targeted edits to the design doc before writing
the Phase 1 implementation plan, even though none of them affects Phase 1
execution itself:

1. §3 Phase 4 row (`:56`) — rewrite to match revised §6 Phase 4 scope
   (Critical C1).
2. §7 Phase 4 exit criterion (`:274`) — change "Four methodology bugs"
   to the actual revised deliverable (Critical C2).
3. §6 model-comparison table (`:260`) — remove or correct "(W875RX1
   dropped)" (Critical C3).
4. §7 / §6 / §3 — pick a consistent model count, 5 or 6 (Critical C4).

The design doc is otherwise structurally sound: §4 structure, §5 tooling,
§8 risks, and §10 self-review hold up. Phase 1 (Foundation: skeleton +
tooling + FRED key rotation) does not depend on any of the contradictions
above and can proceed in parallel with the edits if time pressure is high
— but cleaner to fix the doc first since it is the document a paper
reviewer will eventually read.
