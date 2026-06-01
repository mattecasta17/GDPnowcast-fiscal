# Phase 3 Implementation Plan — Library migration + golden tests (de-MATLAB the DFM)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v1 MATLAB-style DFM pipeline (`Functions/` + `DFM_*.py` + `nowcast_*.py`) into a typed, tested `src/gdpnowcast/` library that reproduces v1's production numbers (proven by a frozen golden baseline), fixes the known v1 bugs, removes the MATLAB date offset, and replaces the 18 per-year backtest scripts with one parameterised runner.

**Architecture:** Three gated parts. **3a-pre (`A0`):** the v1 code does **not run on the locked NumPy 2.4.6** (it uses `np.in1d`, removed in NumPy 2.0, and a `(1,1)`-array→scalar assignment that NumPy 2.0 turned into an error). Apply *minimal, behaviour-preserving* compat shims to `Functions/` so the legacy pipeline runs; this is a prerequisite for the gate and is validated against v1's stored output. **3a (hard gate):** run the (now-runnable) v1 code on the *v1 data backup* (`data/US_*_v1/`) with the **same `sample_start=2000-01-01` v1 used in production**, freeze its outputs to `tests/golden/*.json`, and *assert the re-estimated params match the committed production pickle* `DFM_quarter_param/ResDFM_20161003.pickle` so the golden is provably v1's real numbers. **3b:** port each module into `src/gdpnowcast/` (both golden and port run on the same NumPy 2.4.6, so 1e-6 parity is robust), asserting golden parity at each step. Port-correctness (3b) is verified on the *v1 data*, cleanly separating it from the data-panel differences found in Phase 2 (a Phase 4 concern — see "Open decisions").

**Tech Stack:** Python 3.13, NumPy **2.4.6** (note the version — drives `A0`), scipy (`scipy.linalg.eig`, `block_diag`), pandas, pytest (`-m golden`), mypy (`disallow_untyped_defs`, `warn_unused_ignores`), ruff, `just`.

---

## Context & key findings (read before starting) — all verified against source 2026-06-01

The v1 pipeline, traced end-to-end:

1. **`load_spec(path)`** (`Functions/load_spec.py`, a *class*) parses `Spec_US_new.xlsx`: keeps **`Model==1`** rows, sorts by frequency, exposes numpy-array attributes `SeriesID, SeriesName, Frequency, Units, Transformation, Category, UnitsTransformed` **plus `Blocks` (N×nBlocks) and `BlockNames`**. **`Spec_US_new.xlsx` has 32 rows but only 28 have `Model==1`** — the DFM runs on **28 series, of which 2 are quarterly (`GDPC1`, `ULCNFB`)**. (`A261RX1Q020SBEA`, `HSN1F`, `PPIFIS`, `WHLSLRIMSA` are `Model==0` → excluded.) The Phase-2 `src/gdpnowcast/data/spec.py` counts 32 because it does *not* filter `Model`; the DFM spec loader must filter `Model==1`. The production pickle confirms it: `ResDFM_20161003.pickle` has `C` shape `(28, 56)`, `Mx` length 28.
2. **`load_data(datafile, Spec, sample=None)`** (`Functions/load_data.py`) reads a vintage `.xlsx` (raw `Z`), reorders to `Spec.SeriesID`, **transforms** each series (`lin/chg/ch1/pch/pc1/pca/log`) to `X`, drops the first quarter (`X[3:]`), and (if `sample` given) drops rows before `sample`. `Time = Date.toordinal()+366` (MATLAB offset). **Uses `np.in1d` (line 77) → crashes on NumPy 2.4.6.** The Phase-2 fetcher emits the *raw* `.xlsx`; this transform layer lives in the model pipeline → ported here.
3. **`dfm(X, Spec, threshold=1e-5, max_iter=5000)`** (`Functions/dfm.py`, 1086 ln, Banbura–Modugno EM/Kalman) returns `Res` with keys `x_sm, Z, C, R, A, Q, Mx, Wx, Z_0, V_0, r, p, loglik`. Helpers: `InitCond, EMstep, em_converged, runKF, SKF, FIS, MissData`. **`InitCond` (≈line 404/405) assigns a `(1,1)` array into a scalar slot (`BM[i,i]=…`, `SM[i,i]=…`) → ValueError on NumPy 2.0+.** Support modules: `remNaNs_spline.py`, `decompose_common_factor.py`, `extract_common_residual.py`.
4. **`News_DFM(...)`** (`Functions/update_Nowcast.py:122`) computes the news; it calls **`para_const`** (`update_Nowcast.py:347`), which is the actual Kalman helper that calls `SKF`/`FIS` (lines 399-400). **`para_const` must be ported alongside `News_DFM`.** The thin wrapper **`update_nowcast2(X_old, X_new, Time, Spec, Res, series, period, vintage_old, vintage_new, display)`** (`Functions/update_Nowcast2.py`) returns `{y_old, y_new, impact_revisions, impact_releases, news_table, vintage_old, vintage_new}`. Both apply `+366`; the display path reads `Spec.UnitsTransformed`.
5. **`nowcast_<year>[_fiscal].py`** (18 scripts) drive the backtest: per quarter a hardcoded `vintages_dict`, a `param_map` (`prev`/`curr` **pre-estimated pickle** + `switch_date`), hardcoded `gdp_adv_estimate`. **Crucially, v1 production estimated the params with `sample_start=2000-01-01`** (`DFM_new.py:23,39`) but applies them to **full-sample** vintage data in the news step (`nowcast_2017.py:132-133` call `load_data` with *no* sample). The `param_map` paths are absolute and broken; the pickles exist under `DFM_quarter_param/` (35) and `DFM_quarter_param_fiscal/` (35).

**Bugs to fix in 3b (audit + this read):**
- `Functions/dfm.py:786` — `print('…{} to {}').format(prev,loglik)` calls `.format` on `print()`'s `None` → `AttributeError` when log-lik decreases. Fix: `print('…{} to {}'.format(prev, loglik))`.
- `Functions/dfm.py:124` — `max_iter = 5000` reassigns and ignores the argument. Delete it. (No-op for the golden, which runs at the 5000 cap anyway — but correct.)
- **Unraised `ValueError`s**: `load_data.py:38`, `:148`; the dead `formula_dict["lin"]=lambda x:x*2` landmine (never hit; drop it). `load_spec.py:68` malformed text.
- **`extract_common_residual.py`** — `gdp_resid` hardcoded `0.0` → `share_common` always 1.0/NaN; meaningless. Fix to a real (projection) residual with an honest definition (see B6 caveat).
- **MATLAB `+366`/`-366`** in `load_data.readData`, `update_nowcast2`, drivers — removed; use real `pandas.Timestamp` internally (verified numerically safe for this data — all vintage dates are month-start).

**NumPy-2 incompatibilities (NEW — block the gate; handled in `A0`):** `np.in1d` (`load_data.py:77`) removed in NumPy 2.0 → `AttributeError` (confirmed on 2.4.6); `(1,1)`→scalar assignment in `InitCond` (`dfm.py:404/405`) → `ValueError` in NumPy 2.0+. Both are mechanical, behaviour-preserving to fix (`np.in1d`→`np.isin`; `float(...)`/`.item()`). Scan all of `Functions/` for the same two patterns.

**What is NOT in Phase 3** (per design doc): the `gdpnowcast run` **CLI** and the Streamlit dashboard are **Phase 5**. The 4 methodology fixes (MTSDS133FMS `ch1`, quarterly DM+HLN) **and** the `pca(GDPC1)` BEA-growth regression test are **Phase 4**. Physical deletion of v1 root files is **Phase 5b**. The full multi-year/quarter backtest config and the **fiscal variant** are extended in Phase 4 (this plan proves the machinery on baseline `2017q1`).

## Target file structure (created in 3b)

```
src/gdpnowcast/
├── dfm_spec.py          # DfmSpec dataclass + load_dfm_spec() (Model==1 filter, Blocks-aware, computes UnitsTransformed)
├── transform.py         # vintage .xlsx -> (X, Time, Z); port of load_data.py, offset removed, np.isin, ValueErrors raised
├── dfm.py               # the DFM core (region-sectioned), port of (A0-shimmed) Functions/dfm.py + bug fixes
├── news.py              # para_const + News_DFM + update_nowcast (port of update_Nowcast*.py, offset removed)
├── decomposition.py     # honest GDP common / projection-residual split (replaces extract_common_residual resid=0)
└── nowcast/
    ├── __init__.py
    ├── config.py        # backtest config: per-(year,quarter) vintages, prev/curr/switch, gdp_actuals (2017q1 to start)
    └── runner.py        # parameterised backtest loop -> nowcast/metrics/news frames

tests/
├── golden/
│   ├── dfm_legacy_estimator.json   # 3a: v1 dfm() outputs for 2 vintages (sample_start=2000) + sidecar
│   └── dfm_legacy_nowcast.json     # 3a: v1 2017q1 nowcast outputs (y_old/y_new/impacts)
├── test_dfm_golden.py · test_news_golden.py · test_runner_golden.py
├── test_transform.py · test_dfm_spec.py · test_dfm_support.py · test_decomposition.py
```

---

# PART A0 — NumPy-2 compatibility for the legacy pipeline (prerequisite for the gate)

> The v1 code must *run* before it can be frozen. These shims are mechanical and behaviour-preserving; A2 validates them against the committed production pickle.

### Task A0: Make `Functions/` run on NumPy 2.4.6

**Files:** Modify `Functions/load_data.py`, `Functions/dfm.py` (and any other file matching the two patterns).

- [ ] **Step 1: Find every NumPy-2 breakage**

Run: `uv run python -c "import numpy as np; print(np.__version__, hasattr(np,'in1d'))"` → expect `2.4.6 False`.
Grep the legacy tree:
```bash
grep -rn "np.in1d\|\.in1d(" Functions/ DFM_new.py DFM_fiscal.py nowcast_*.py
grep -rn "\[i,i\] *=\|\[i, i\] *=" Functions/dfm.py
```
Expected: `load_data.py:77` (`np.in1d`); `dfm.py` `BM[i,i]=`, `SM[i,i]=` near 404/405.

- [ ] **Step 2: Shim `np.in1d` → `np.isin` (identical semantics)**

In `Functions/load_data.py:77`, change `np.in1d(Mnem, Spec.SeriesID)` → `np.isin(Mnem, Spec.SeriesID)`. (`np.isin` is the documented drop-in replacement; same boolean mask.)

- [ ] **Step 3: Shim the `(1,1)`→scalar assignment**

In `Functions/dfm.py` `InitCond`, wrap the offending RHS in `float(...)`:
```python
BM[i, i] = float(np.matmul(np.matmul(np.linalg.inv(...), res_i[:-1].T), res_i[1:]))
SM[i, i] = float(...)   # the matching SM line
```
Copy the exact RHS from the current file; only add `float(...)`. `float()` of a `(1,1)` array equals the scalar NumPy<2 used to coerce — behaviour-preserving.

- [ ] **Step 4: Verify the legacy estimator now runs**

Run:
```bash
uv run python -c "from Functions.load_spec import load_spec; from Functions.load_data import load_data; from Functions.dfm import dfm; s=load_spec('Spec_US_new.xlsx'); X,_,_=load_data('data/US_new_v1/2016-10-03.xlsx', s, __import__('datetime').date(2000,1,1).toordinal()+366); R=dfm(X,s,1e-4); print('OK', R['C'].shape, R['loglik'][-1])"
```
Expected: prints `OK (28, 56) <finite negative loglik>`. If a *new* `(1,1)`-assignment ValueError appears deeper (EMstep/SKF/FIS), apply the same `float(...)` shim there and re-run (these are the only two NumPy-2 patterns; fix each occurrence). Do NOT change any numerical expression beyond `in1d→isin` and the scalar coercion.

- [ ] **Step 5: Commit the shims (documented, behaviour-preserving)**

```bash
git add Functions/load_data.py Functions/dfm.py
git commit -m "compat(v1): NumPy-2 shims (np.in1d->np.isin, (1,1)->scalar) so the legacy DFM runs

Prerequisite for the Phase-3a golden gate: the locked NumPy 2.4.6 removed
np.in1d and turned (1,1)-array->scalar assignment into a ValueError. Both
shims are behaviour-preserving; A2 validates the result against the committed
production pickle ResDFM_20161003.pickle."
```

---

# PART A — Phase 3a (HARD GATE: freeze the golden, then stop)

> Only *reads* the (A0-shimmed) v1 code; *writes* JSON goldens + freeze scripts under `tools/`. No `src/gdpnowcast/` model code until Part A is committed.

### Task A1: Golden-freeze harness for the DFM estimator (sample_start=2000, fidelity-checked vs pickle)

**Files:** Create `tools/freeze_golden.py`; create `tests/golden/.gitkeep`.

- [ ] **Step 1: Create the freeze script**

`tools/freeze_golden.py`:
```python
"""Phase 3a: freeze the v1 DFM estimator golden by running the (A0-shimmed) v1
code on the v1 data backup, with sample_start=2000-01-01 (matching DFM_new.py /
the production pickles). Asserts the re-estimated Res matches the committed
pickle so the golden is provably v1's production numbers. Run once; commit JSON.

Usage:  uv run python tools/freeze_golden.py
"""
from __future__ import annotations

import json
import pickle
import platform
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import scipy

from Functions.dfm import dfm
from Functions.load_data import load_data
from Functions.load_spec import load_spec

REPO = Path(__file__).resolve().parents[1]
THRESHOLD = 1e-4                                   # DFM_new.py:77
SAMPLE_START = date(2000, 1, 1).toordinal() + 366  # DFM_new.py:23 (MATLAB ordinal)
# Two quarter-start vintages = the prev/curr params for the 2017q1 nowcast golden.
# Each maps to a committed production pickle for the fidelity check.
VINTAGES = {"2016-10-03": "ResDFM_20161003.pickle",
            "2017-01-03": "ResDFM_20170103.pickle"}


def _digest(a: np.ndarray) -> dict:
    arr = np.asarray(a, dtype=float)
    return {"shape": list(arr.shape), "nansum": float(np.nansum(arr)),
            "nansumsq": float(np.nansum(arr**2))}


def main() -> None:
    spec = load_spec("Spec_US_new.xlsx")
    payload: dict = {"meta": {}, "vintages": {}}
    for v, pkl in VINTAGES.items():
        X, _, _ = load_data(str(REPO / "data" / "US_new_v1" / f"{v}.xlsx"), spec, SAMPLE_START)
        Res = dfm(X, spec, THRESHOLD)
        # Fidelity check vs the committed production pickle (made by v1 on NumPy<2).
        ref = pickle.load(open(REPO / "DFM_quarter_param" / pkl, "rb"))["Res"]
        max_dC = float(np.max(np.abs(np.asarray(Res["C"]) - np.asarray(ref["C"]))))
        print(f"{v}: re-estimated vs pickle max|dC| = {max_dC:.3e}  (C shape {Res['C'].shape})")
        payload["vintages"][v] = {
            "X_shape": list(np.asarray(X).shape),
            "n_series": int(np.asarray(Res["C"]).shape[0]),
            "loglik_final": float(Res["loglik"][-1]),
            "C": np.asarray(Res["C"]).tolist(), "A": np.asarray(Res["A"]).tolist(),
            "Q": np.asarray(Res["Q"]).tolist(), "R": np.asarray(Res["R"]).tolist(),
            "Z_0": np.asarray(Res["Z_0"]).tolist(), "V_0": np.asarray(Res["V_0"]).tolist(),
            "Mx": np.asarray(Res["Mx"]).tolist(), "Wx": np.asarray(Res["Wx"]).tolist(),
            "x_sm_digest": _digest(Res["x_sm"]), "Z_digest": _digest(Res["Z"]),
            "x_sm_gdp_tail": [float(x) for x in np.asarray(Res["x_sm"])[-6:,
                              int(np.where(spec.SeriesID == "GDPC1")[0][0])]],
            "pickle_max_abs_dC": max_dC,
        }
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
    payload["meta"] = {"v1_commit": sha, "data_source": "data/US_new_v1",
                       "threshold": THRESHOLD, "sample_start_iso": "2000-01-01",
                       "numpy": np.__version__, "scipy": scipy.__version__,
                       "python": platform.python_version(),
                       "note": "v1 code with A0 NumPy-2 shims; pickle_max_abs_dC records "
                               "agreement with the NumPy<2 production pickle"}
    out = REPO / "tests" / "golden" / "dfm_legacy_estimator.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create the golden dir marker + commit harness**

```bash
New-Item -ItemType File tests/golden/.gitkeep   # PowerShell
git add tools/freeze_golden.py tests/golden/.gitkeep
git commit -m "test(phase3a): golden-freeze harness for the v1 DFM estimator"
```

### Task A2: Generate + commit the estimator golden (and record pickle agreement)

- [ ] **Step 1: Run it**

Run: `uv run python tools/freeze_golden.py`
Expected: two `re-estimated vs pickle max|dC| = …` lines and `wrote …`. **Record the `max|dC|` values** — they quantify how well the A0-shimmed/NumPy-2.4 re-estimation reproduces the NumPy<2 production pickle.
- If `max|dC| ≲ 1e-6`: shims + NumPy-2 reproduce v1 production → strongest case; the golden *is* v1's numbers.
- If `1e-6 < max|dC| ≲ 1e-3`: small cross-NumPy drift; the golden is "v1 behaviour on NumPy-2" (still a sound port reference). **Document the value in `docs/data_sources.md`/RESUME and loosen the 3b parity tol to match (e.g. `atol=1e-5`).**
- If `max|dC| ≫ 1e-3`: STOP — the shims changed behaviour or the spec/sample is wrong; investigate before committing.

- [ ] **Step 2: Sanity-check**

Run: `uv run python -c "import json; d=json.load(open('tests/golden/dfm_legacy_estimator.json')); v=d['vintages']['2016-10-03']; print('n_series', v['n_series'], 'C', len(v['C']), 'x', len(v['C'][0]), 'pkl_dC', v['pickle_max_abs_dC'])"`
Expected: `n_series 28`, `C 28`, `x 56`, small `pkl_dC`.

- [ ] **Step 3: Commit**

```bash
git add tests/golden/dfm_legacy_estimator.json
git commit -m "test(phase3a): freeze v1 DFM estimator golden (28 series, sample_start=2000, pickle-checked)"
```

### Task A3: Generate + commit the end-to-end nowcast golden (2017q1)

**Files:** Create `tools/freeze_golden_nowcast.py`; create `tests/golden/dfm_legacy_nowcast.json`.

- [ ] **Step 1: Create the nowcast freeze script**

`tools/freeze_golden_nowcast.py`:
```python
"""Phase 3a: freeze the v1 2017q1 nowcast golden by running the (A0-shimmed) v1
update_nowcast2 on the v1 data backup. Params estimated with sample_start=2000
(matching production); the news step uses FULL-sample data (matching
nowcast_2017.py, which calls load_data without a sample arg).

Usage:  uv run python tools/freeze_golden_nowcast.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

from Functions.dfm import dfm
from Functions.load_data import load_data
from Functions.load_spec import load_spec
from Functions.update_Nowcast2 import update_nowcast2

REPO = Path(__file__).resolve().parents[1]
THRESHOLD = 1e-4
SAMPLE_START = date(2000, 1, 1).toordinal() + 366
SERIES, PERIOD = "GDPC1", "2017q1"
SWITCH = np.datetime64("2017-01-01")
VINTAGES = [
    "2016-12-02", "2016-12-09", "2016-12-16", "2016-12-23", "2016-12-30",
    "2017-01-06", "2017-01-13", "2017-01-20", "2017-01-27",
    "2017-02-03", "2017-02-10", "2017-02-17", "2017-02-24",
    "2017-03-03", "2017-03-10", "2017-03-17", "2017-03-24", "2017-03-31",
    "2017-04-07", "2017-04-14", "2017-04-21", "2017-04-28",
]


def vfile(v: str) -> str:
    return str(REPO / "data" / "US_new_v1" / f"{v}.xlsx")


def main() -> None:
    spec = load_spec("Spec_US_new.xlsx")
    Xp, _, _ = load_data(vfile("2016-10-03"), spec, SAMPLE_START)   # prev params
    Res_prev = dfm(Xp, spec, THRESHOLD)
    Xc, _, _ = load_data(vfile("2017-01-03"), spec, SAMPLE_START)   # curr params
    Res_curr = dfm(Xc, spec, THRESHOLD)

    rows = []
    for i in range(1, len(VINTAGES)):
        v_old, v_new = VINTAGES[i - 1], VINTAGES[i]
        Res_use = Res_prev if np.datetime64(v_new) < SWITCH else Res_curr
        X_old, _, _ = load_data(vfile(v_old), spec)          # news step: FULL sample
        X_new, Time, _ = load_data(vfile(v_new), spec)
        r = update_nowcast2(X_old, X_new, Time, spec, Res_use, SERIES, PERIOD,
                            v_old, v_new, display=False)
        rows.append({"vintage": v_new, "y_old": float(r["y_old"][0]),
                     "y_new": float(r["y_new"][0]),
                     "impact_revisions": float(r["impact_revisions"][0]),
                     "impact_releases": float(np.nansum(r["impact_releases"]))})
    out = REPO / "tests" / "golden" / "dfm_legacy_nowcast.json"
    out.write_text(json.dumps({"period": PERIOD, "series": SERIES,
                               "sample_start_iso": "2000-01-01", "rows": rows}, indent=2),
                   encoding="utf-8")
    print(f"wrote {out} ({len(rows)} vintage pairs)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run + commit**

Run: `uv run python tools/freeze_golden_nowcast.py` → `wrote … (21 vintage pairs)`; `y_new` values O(1) near the 2017q1 advance estimate (0.7).
```bash
git add tools/freeze_golden_nowcast.py tests/golden/dfm_legacy_nowcast.json
git commit -m "test(phase3a): freeze v1 2017q1 nowcast golden (params@2000, news@full-sample, v1 data)"
```

### Task A4: Mark the 3a gate

- [ ] **Step 1:** In `RESUME.md`, record: golden frozen from A0-shimmed v1 on v1 data; `pickle_max_abs_dC` value; the chosen 3b parity tolerance; no de-MATLAB edit precedes this commit. **Step 2:** `git add RESUME.md && git commit -m "docs(phase3a): record golden-baseline gate + pickle agreement"`.

> **GATE:** Part B begins only after A0 + A1–A4 are committed. Use the tolerance chosen in A2 (`TOL`) everywhere below; default `rtol=1e-6, atol=1e-6`, relaxed if A2 showed cross-NumPy drift.

---

# PART B — Phase 3b (de-MATLAB port + runner)

### Task B1: DFM spec loader (Model==1 filter, Blocks-aware, full attribute set)

**Files:** Create `src/gdpnowcast/dfm_spec.py`; Test `tests/test_dfm_spec.py`.

- [ ] **Step 1: Write the failing test (spec-derived, not hardcoded magic numbers)**

`tests/test_dfm_spec.py`:
```python
from gdpnowcast.dfm_spec import load_dfm_spec


def test_spec_model1_blocks_and_quarterly() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    assert len(spec.series_id) == 28                       # Model==1 rows (32 in file, 4 are Model==0)
    assert spec.blocks.shape[0] == len(spec.series_id)     # one block-row per kept series
    assert (spec.blocks[:, 0] == 1).all()                  # all load on the global block
    assert set(spec.series_id[spec.frequency == "q"]) == {"GDPC1", "ULCNFB"}
    assert len(spec.units_transformed) == len(spec.series_id)  # display field present
```

- [ ] **Step 2:** Run → `ModuleNotFoundError` (FAIL).

- [ ] **Step 3: Implement `load_dfm_spec`** (typed port of `Functions/load_spec.py`; filters `Model==1`, computes `UnitsTransformed`, no print side-effect)

`src/gdpnowcast/dfm_spec.py`:
```python
"""Blocks-aware DFM spec loader — typed port of Functions/load_spec.py.
Separate from data/spec.py (the fetcher spec): the DFM needs the block-loading
matrix, the Model==1 filter, and frequency-sorted numpy arrays."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

_FREQ_ORDER = ["d", "w", "m", "q", "sa", "a"]
_FIELDS = ["SeriesID", "SeriesName", "Frequency", "Units", "Transformation", "Category"]
_UNITS_T = {"lin": "Levels (No Transformation)", "chg": "Change (Difference)",
            "ch1": "Year over Year Change (Difference)", "pch": "Percent Change",
            "pc1": "Year over Year Percent Change", "pca": "Percent Change (Annual Rate)",
            "cch": "Continuously Compounded Rate of Change",
            "cca": "Continuously Compounded Annual Rate of Change", "log": "Natural Log"}


@dataclass(frozen=True)
class DfmSpec:
    series_id: np.ndarray
    series_name: np.ndarray
    frequency: np.ndarray
    units: np.ndarray
    transformation: np.ndarray
    category: np.ndarray
    units_transformed: np.ndarray
    blocks: np.ndarray
    block_names: list[str]

    # v1-compatible aliases so the verbatim-ported dfm.py / News_DFM bodies work unedited.
    @property
    def Blocks(self) -> np.ndarray: return self.blocks          # noqa: N802, E704
    @property
    def SeriesID(self) -> np.ndarray: return self.series_id     # noqa: N802, E704
    @property
    def SeriesName(self) -> np.ndarray: return self.series_name  # noqa: N802, E704
    @property
    def Frequency(self) -> np.ndarray: return self.frequency    # noqa: N802, E704
    @property
    def Units(self) -> np.ndarray: return self.units            # noqa: N802, E704
    @property
    def Category(self) -> np.ndarray: return self.category      # noqa: N802, E704
    @property
    def Transformation(self) -> np.ndarray: return self.transformation  # noqa: N802, E704
    @property
    def UnitsTransformed(self) -> np.ndarray: return self.units_transformed  # noqa: N802, E704
    @property
    def BlockNames(self) -> list[str]: return self.block_names  # noqa: N802, E704


def load_dfm_spec(filename: str | Path) -> DfmSpec:
    raw = pd.read_excel(filename)
    raw.columns = [c.replace(" ", "") for c in raw.columns]
    raw = raw[raw["Model"] == 1].reset_index(drop=True)

    order: list[int] = []
    for freq in _FREQ_ORDER:
        order += list(raw[raw.Frequency == freq].index)
    raw = raw.loc[order, :]

    for field in _FIELDS:
        if field not in raw.columns:
            raise ValueError(f"{field}: column missing from model specification.")

    block_cols = list(raw.columns[raw.columns.str.contains("Block", case=False)])
    blocks = raw[block_cols].copy()
    blocks[blocks.isna()] = 0
    if not (blocks.iloc[:, 0] == 1).all():
        raise ValueError("All variables must load on the global block.")

    transformation = raw["Transformation"].to_numpy(copy=True)
    return DfmSpec(
        series_id=raw["SeriesID"].to_numpy(copy=True),
        series_name=raw["SeriesName"].to_numpy(copy=True),
        frequency=raw["Frequency"].to_numpy(copy=True),
        units=raw["Units"].to_numpy(copy=True),
        transformation=transformation,
        category=raw["Category"].to_numpy(copy=True),
        units_transformed=np.array([_UNITS_T[t] for t in transformation]),
        blocks=blocks.to_numpy(copy=True),
        block_names=[re.sub("Block[0-9]+-", "", c) for c in block_cols],
    )
```

- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `git add src/gdpnowcast/dfm_spec.py tests/test_dfm_spec.py && git commit -m "feat(dfm): Model==1, Blocks-aware DfmSpec loader (port of load_spec)"`.

### Task B2: Data transform (vintage .xlsx → X), offset removed, `np.isin`, ValueErrors raised

**Files:** Create `src/gdpnowcast/transform.py`; Test `tests/test_transform.py`.

- [ ] **Step 1: Parity test vs the (A0-shimmed) v1 `load_data`** — `tests/test_transform.py`:
```python
import numpy as np

from Functions.load_data import load_data as v1_load_data
from Functions.load_spec import load_spec as v1_load_spec
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

VINT = "data/US_new_v1/2017-01-03.xlsx"


def test_transform_matches_v1_X() -> None:
    X1, _, _ = v1_load_data(VINT, v1_load_spec("Spec_US_new.xlsx"))
    X2, _, _ = load_vintage(VINT, load_dfm_spec("Spec_US_new.xlsx"))
    assert X1.shape == X2.shape
    assert np.array_equal(np.isnan(X1), np.isnan(X2))
    np.testing.assert_allclose(np.nan_to_num(X1), np.nan_to_num(X2), rtol=0, atol=0)
```

- [ ] **Step 2:** Run → FAIL (ImportError).

- [ ] **Step 3: Implement `transform.py`** (port of `load_data.py`; **`np.isin`** not `np.in1d`; **`+366` removed** → `Time` is a `DatetimeIndex`; **raise** ValueErrors; drop the `lin:x*2` dead lambda):

`src/gdpnowcast/transform.py`:
```python
"""Vintage .xlsx -> (X transformed, Time, Z raw) for the DFM.
Typed port of Functions/load_data.py: MATLAB +366 removed (Time is a real
DatetimeIndex), np.in1d->np.isin, unraised ValueErrors fixed, dead lin:x*2
lambda dropped. Numerically identical to v1 on X (tests/test_transform.py)."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .dfm_spec import DfmSpec

_FREQ_STEP = {"m": 1, "q": 3}


def _read(datafile: str) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    if os.path.splitext(datafile)[1] not in (".xlsx", ".xls"):
        raise ValueError("File is not an Excel file")
    dat = pd.read_excel(datafile)
    mnem = np.array([c for c in dat.columns if c != "Date"])
    return dat[mnem].to_numpy(copy=True), pd.DatetimeIndex(pd.to_datetime(dat["Date"])), mnem


def _sort(z: np.ndarray, mnem: np.ndarray, spec: DfmSpec) -> np.ndarray:
    keep = np.isin(mnem, spec.series_id)
    mnem, z = mnem[keep], z[:, keep]
    perm = np.array([np.where(mnem == s)[0][0] for s in spec.series_id])
    return z[:, perm]


def _transform(z: np.ndarray, spec: DfmSpec) -> np.ndarray:
    t, n = z.shape
    x = np.full((t, n), np.nan)
    for i in range(n):
        f = spec.transformation[i]
        step = _FREQ_STEP[spec.frequency[i]]
        t1 = step - 1
        years = step / 12
        col = z[:, i].copy()
        if f == "lin":
            x[:, i] = col
        elif f == "chg":
            x[t1::step, i] = np.append(np.nan, col[t1 + step::step] - col[t1:-1 - t1:step])
        elif f == "ch1":
            x[12 + t1::step, i] = col[12 + t1::step] - col[t1:-12:step]
        elif f == "pch":
            x[t1::step, i] = (np.append(np.nan, col[t1 + step::step] / col[t1:-1 - t1:step]) - 1) * 100
        elif f == "pc1":
            x[12 + t1::step, i] = ((col[12 + t1::step] / col[t1:-12:step]) - 1) * 100
        elif f == "pca":
            x[t1::step, i] = (np.append(np.nan, col[t1 + step::step] / col[t1:-step:step]) ** (1 / years) - 1) * 100
        elif f == "log":
            x[:, i] = np.log(col)
        else:
            raise ValueError(f"{f}: transformation is unknown")
    return x


def load_vintage(
    datafile: str, spec: DfmSpec, sample_start: pd.Timestamp | None = None
) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    z, time, mnem = _read(datafile)
    z = _sort(z, mnem, spec)
    x = _transform(z, spec)
    x, time, z = x[3:, :], time[3:], z[3:, :]            # drop first quarter
    if sample_start is not None:
        keep = time >= sample_start
        x, time, z = x[keep, :], time[keep], z[keep, :]
    return x, time, z
```

- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `git commit -m "feat(dfm): vintage transform (port of load_data); offset removed, np.isin, ValueErrors raised"`.

### Task B3: Port the DFM support modules

**Files:** Create `src/gdpnowcast/_dfm_support.py` (`rem_nans_spline`, `decompose_common_factor`); Test `tests/test_dfm_support.py`.

- [ ] **Step 1: Parity test** for `rem_nans_spline` vs `Functions/remNaNs_spline.py` (synthetic input, `method=2,k=3`), asserting equal output + NaN mask. **Step 2:** Run → FAIL. **Step 3:** Copy the two module bodies verbatim into `_dfm_support.py` (rename `remNaNs_spline`→`rem_nans_spline`), add `from __future__ import annotations` + type hints on the public signatures; **scan for the two NumPy-2 patterns** and apply the same shims if present (they were not in A0's grep of `Functions/`, but re-check). **Step 4:** Run → PASS. **Step 5:** Commit.

### Task B4: Port the DFM core + fix the estimator bugs (golden parity)

**Files:** Create `src/gdpnowcast/dfm.py`; Test `tests/test_dfm_golden.py`.

- [ ] **Step 1: Golden parity test** — `tests/test_dfm_golden.py`:
```python
import json
from pathlib import Path

import numpy as np
import pytest

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_estimator.json").read_text())
TOL = dict(rtol=1e-6, atol=1e-6)   # relax per A2 if pickle_max_abs_dC showed drift
SAMPLE_START = __import__("pandas").Timestamp("2000-01-01")
pytestmark = [pytest.mark.golden,
              pytest.mark.skipif(not Path("data/US_new_v1").exists(),
                                 reason="v1 data backup absent")]


@pytest.mark.parametrize("vintage", list(GOLDEN["vintages"]))
def test_dfm_matches_legacy_golden(vintage: str) -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    x, _, _ = load_vintage(f"data/US_new_v1/{vintage}.xlsx", spec, SAMPLE_START)
    res = dfm(x, spec, GOLDEN["meta"]["threshold"])
    g = GOLDEN["vintages"][vintage]
    assert res["C"].shape[0] == g["n_series"] == 28
    assert res["loglik"][-1] == pytest.approx(g["loglik_final"], **TOL)
    for k in ("C", "A", "Q", "R", "Z_0", "V_0", "Mx", "Wx"):
        np.testing.assert_allclose(np.asarray(res[k]), np.asarray(g[k]), **TOL)
    i_gdp = int(np.where(spec.series_id == "GDPC1")[0][0])
    np.testing.assert_allclose(np.asarray(res["x_sm"])[-6:, i_gdp],
                               np.asarray(g["x_sm_gdp_tail"]), **TOL)
```
> Note `load_vintage(..., SAMPLE_START)` — the estimator golden used `sample_start=2000-01-01`; the parity test MUST pass the same Timestamp or it estimates on a different sample and fails.

- [ ] **Step 2:** Run → FAIL (ImportError).

- [ ] **Step 3: Create `src/gdpnowcast/dfm.py` by copying the (A0-shimmed) `Functions/dfm.py` verbatim, then apply exactly:**
  1. `from __future__ import annotations`; `from ._dfm_support import rem_nans_spline` (replace `remNaNs_spline(` calls); keep `from scipy.linalg import eig, block_diag`; import `DfmSpec` for typing.
  2. Delete the duplicate `max_iter = 5000` (≈ line 124) so the argument is honoured.
  3. Fix `em_converged` (≈ line 786): `print("******likelihood decreased from {} to {}".format(previous_loglik, loglik))`.
  4. The `(1,1)`→scalar `float(...)` shims from A0 are already present (carried over by the verbatim copy) — keep them.
  5. Gate the side-effect `print(...)` calls ("Table 3", "Estimating…") behind `verbose: bool = False` (output-only; no numerics).
  6. Type the public signature: `def dfm(X: np.ndarray, spec: DfmSpec, threshold: float = 1e-5, max_iter: int = 5000, verbose: bool = False) -> dict:`. Add `# region:` markers around `dfm / InitCond / EMstep / Kalman (runKF,SKF,FIS,MissData)`.

- [ ] **Step 4:** Run `uv run pytest -m golden tests/test_dfm_golden.py -v` → 2 passed. Mismatch ⇒ a port edit changed a numerical op; diff against the A0-shimmed `Functions/dfm.py` line-by-line; do NOT loosen `TOL` beyond the A2-justified value.

- [ ] **Step 5:** Commit `git commit -m "feat(dfm): port DFM core (de-MATLAB); fix print/max_iter bugs; golden parity"`.

### Task B5: Port the news module (`para_const` + `News_DFM` + `update_nowcast`), offset removed (golden parity)

**Files:** Create `src/gdpnowcast/news.py`; Test `tests/test_news_golden.py`.

- [ ] **Step 1: Nowcast golden parity test** — `tests/test_news_golden.py`:
```python
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.news import update_nowcast
from gdpnowcast.transform import load_vintage

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_nowcast.json").read_text())
TOL = dict(rtol=1e-6, atol=1e-6)
SAMPLE_START = pd.Timestamp("2000-01-01")
SWITCH = pd.Timestamp("2017-01-01")
pytestmark = [pytest.mark.golden,
              pytest.mark.skipif(not Path("data/US_new_v1").exists(),
                                 reason="v1 data backup absent")]


def _v(v: str) -> str:
    return f"data/US_new_v1/{v}.xlsx"


def test_news_matches_legacy_nowcast_golden() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    res_prev = dfm(load_vintage(_v("2016-10-03"), spec, SAMPLE_START)[0], spec, 1e-4)
    res_curr = dfm(load_vintage(_v("2017-01-03"), spec, SAMPLE_START)[0], spec, 1e-4)
    order = [r["vintage"] for r in GOLDEN["rows"]]
    for idx, row in enumerate(GOLDEN["rows"]):
        v_new = row["vintage"]
        v_old = "2016-12-02" if idx == 0 else order[idx - 1]
        res_use = res_prev if pd.Timestamp(v_new) < SWITCH else res_curr
        x_old, _, _ = load_vintage(_v(v_old), spec)             # news step: full sample
        x_new, time, _ = load_vintage(_v(v_new), spec)
        out = update_nowcast(x_old, x_new, time, spec, res_use, "GDPC1", "2017q1", v_old, v_new)
        assert float(out["y_new"][0]) == pytest.approx(row["y_new"], **TOL)
        assert float(out["y_old"][0]) == pytest.approx(row["y_old"], **TOL)
```

- [ ] **Step 2:** Run → FAIL (ImportError).

- [ ] **Step 3: Port into `src/gdpnowcast/news.py`** — **copy BOTH `News_DFM` and its helper `para_const`** from `Functions/update_Nowcast.py` (verbatim bodies; `para_const` is what calls `SKF`/`FIS`), plus the `update_nowcast2` wrapper renamed `update_nowcast`. Apply:
  1. `from .dfm import SKF, FIS`; import `DfmSpec`. Re-scan the copied bodies for the two NumPy-2 patterns; shim if present.
  2. **Remove `+366`**: in `update_nowcast` replace `dt.strptime(...).toordinal()+366` with `pd.Timestamp(...)`; replace the `future` ordinal loop with `time[-1] + pd.offsets.MonthBegin(i)` (i=1..12); keep `time` a `DatetimeIndex` via `time = time.append(pd.DatetimeIndex(future))` (NOT `np.hstack`); replace `np.where((dt(y,m,d).toordinal()+366)==Time)` with `np.where(time == pd.Timestamp(y, m, 1))`. Keep the 12-row NaN padding of `X_old`/`X_new` and the `News_DFM` calls unchanged.
  3. **API change (document it):** return `vintage_old`/`vintage_new` as ISO strings / `pd.Timestamp`, NOT MATLAB int ordinals — this is intentional (offset removal). Keep all other keys (`y_old, y_new, impact_revisions, impact_releases, news_table`) identical.
  4. Gate the `display` print block behind `verbose: bool = False` (it reads `spec.UnitsTransformed`, now provided by `DfmSpec`).

- [ ] **Step 4:** Run `uv run pytest -m golden tests/test_news_golden.py -v` → PASS (21 pairs within `TOL`). Mismatch ⇒ check `t_nowcast` still selects the same row after offset removal.

- [ ] **Step 5:** Commit `git commit -m "feat(dfm): port para_const+News_DFM+update_nowcast; remove +366 offset; golden parity"`.

### Task B6: Replace `extract_common_residual` with an honest decomposition

> The v1 module hardcoded the residual to `0.0` (so `share_common`≡1). The *correct* common/idiosyncratic split requires the augmented Kalman states (idiosyncratic AR(1) component) — that full decomposition is deferred to **Phase 7** (where it matters). Phase 3 ships the honest **projection** version with a non-tautological test and a docstring that names exactly what it is.

**Files:** Create `src/gdpnowcast/decomposition.py`; Test `tests/test_decomposition.py`.

- [ ] **Step 1: Non-tautological test** — `tests/test_decomposition.py`:
```python
from pathlib import Path

import numpy as np
import pytest

from gdpnowcast.decomposition import gdp_common_share
from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

pytestmark = pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent")


def test_common_share_is_nontrivial_when_gdp_observed() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    x, _, _ = load_vintage("data/US_new_v1/2017-01-03.xlsx", spec, __import__("pandas").Timestamp("2000-01-01"))
    res = dfm(x, spec, 1e-4)
    d = gdp_common_share(x, spec, res, series="GDPC1")
    # The v1 bug forced share_common==1.0 (resid hardcoded 0). A real split must NOT.
    assert np.isfinite(d["gdp_common"])
    assert d["share_common"] != pytest.approx(1.0)      # would fail on the v1 bug
    assert 0.0 < d["share_common"] < 1.5                # plausible magnitude, not degenerate
```

- [ ] **Step 2:** Run → FAIL (ImportError).

- [ ] **Step 3: Implement** `gdp_common_share` (port the SKF call; idiosyncratic = observed − common **projection**; honest docstring):
```python
"""GDP common-component share at the latest observed period.

Fixes Functions/extract_common_residual.py, which hardcoded the residual to 0.0
(share_common ≡ 1). Here the residual is the genuine *projection* residual
(observed − C·f), de-standardised. NOTE: this is the one-step projection
residual, NOT the model's idiosyncratic AR(1) state — the full state-based
decomposition is a Phase 7 deliverable. The test asserts the share is not the
degenerate 1.0 the v1 bug produced."""
from __future__ import annotations

import numpy as np

from .dfm import SKF
from .dfm_spec import DfmSpec


def gdp_common_share(x: np.ndarray, spec: DfmSpec, res: dict, series: str = "GDPC1") -> dict:
    n = res["C"].shape[0]
    xn = x.T if x.shape[0] != n else x                     # (N, T)
    f_last = SKF(xn, res["A"], res["C"], res["Q"], res["R"], res["Z_0"], res["V_0"])["Zm"][:, -1]
    i = int(np.where(np.asarray(spec.series_id) == series)[0][0])
    wx, mx = res["Wx"][i], res["Mx"][i]
    common = float(np.dot(res["C"][i, :], f_last)) * wx + mx
    obs_std = xn[i, -1]
    if np.isnan(obs_std):
        total, resid = common, 0.0
    else:
        total = float(obs_std) * wx + mx
        resid = total - common
    return {"series": series, "gdp_total": total, "gdp_common": common,
            "gdp_proj_residual": resid,
            "share_common": np.nan if total == 0 else common / total}
```

- [ ] **Step 4:** Run → PASS (`share_common` finite, ≠ 1.0). **Step 5:** Commit `git commit -m "fix(dfm): honest GDP common-share (projection residual); v1 hardcoded resid=0"`.

### Task B7: Parameterised backtest runner (deduplicate the 18 scripts)

**Files:** Create `src/gdpnowcast/nowcast/{__init__.py,config.py,runner.py}`; Test `tests/test_runner_golden.py`.

- [ ] **Step 1: Config** — `src/gdpnowcast/nowcast/config.py` with a frozen `QuarterCfg(period, vintages, gdp_actual, prev_vintage, curr_vintage, switch_date)` and the **2017q1** entry ported from `nowcast_2017.py` (the 22 vintages, `gdp_actual=0.7`, `prev="2016-10-03"`, `curr="2017-01-03"`, `switch="2017-01-01"`). The runner re-estimates prev/curr (no opaque pickles; broken absolute paths gone).

- [ ] **Step 2: Runner golden parity test** — `tests/test_runner_golden.py` calling `run_quarter(CONFIG_2017Q1, data_subdir="US_new_v1", spec_file="Spec_US_new.xlsx", series="GDPC1")` and asserting each `y_new` matches `dfm_legacy_nowcast.json` within `TOL`. Guard with the `data/US_new_v1` skipif + `pytest.mark.golden`.

- [ ] **Step 3:** Run → FAIL.

- [ ] **Step 4: Implement `run_quarter`** in `src/gdpnowcast/nowcast/runner.py`:
```python
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..dfm import dfm
from ..dfm_spec import load_dfm_spec
from ..news import update_nowcast
from ..transform import load_vintage
from .config import QuarterCfg

_REPO = Path(__file__).resolve().parents[3]
_SAMPLE_START = pd.Timestamp("2000-01-01")   # match v1 production params


def _vfile(subdir: str, v: str) -> str:
    return str(_REPO / "data" / subdir / f"{v}.xlsx")


def run_quarter(cfg: QuarterCfg, data_subdir: str, spec_file: str,
                series: str = "GDPC1") -> pd.DataFrame:
    spec = load_dfm_spec(spec_file)
    res_prev = dfm(load_vintage(_vfile(data_subdir, cfg.prev_vintage), spec, _SAMPLE_START)[0], spec, 1e-4)
    res_curr = dfm(load_vintage(_vfile(data_subdir, cfg.curr_vintage), spec, _SAMPLE_START)[0], spec, 1e-4)
    switch = pd.Timestamp(cfg.switch_date)
    rows = []
    for i in range(1, len(cfg.vintages)):
        v_old, v_new = cfg.vintages[i - 1], cfg.vintages[i]
        res_use = res_prev if pd.Timestamp(v_new) < switch else res_curr
        x_old, _, _ = load_vintage(_vfile(data_subdir, v_old), spec)        # full sample
        x_new, time, _ = load_vintage(_vfile(data_subdir, v_new), spec)
        out = update_nowcast(x_old, x_new, time, spec, res_use, series, cfg.period, v_old, v_new)
        y_new = float(out["y_new"][0])
        rows.append({"vintage": v_new, "y_old": float(out["y_old"][0]), "y_new": y_new,
                     "error": cfg.gdp_actual - y_new,
                     "impact_revisions": float(out["impact_revisions"][0]),
                     "impact_releases": float(np.nansum(out["impact_releases"]))})
    return pd.DataFrame(rows)
```

- [ ] **Step 5:** Run → PASS. **Step 6:** Commit `git commit -m "feat(nowcast): parameterised runner (dedupe 18 scripts); 2017q1 golden parity"`.

### Task B8: mypy + CI + Phase-3 exit

**Files:** Modify `justfile`, `RESUME.md`.

- [ ] **Step 1:** Add a `test-golden: uv run pytest -m golden -v` recipe to `justfile`. The `golden` marker is already registered in `pyproject.toml`. Golden tests already carry the `data/US_new_v1` skipif so CI (no data) skips them; `just test` stays `-m "not slow"`.
- [ ] **Step 2: Type the helpers.** `pyproject.toml` sets `disallow_untyped_defs=true` AND `warn_unused_ignores=true`, so a verbatim port will NOT pass clean — **budget time to add real return-type hints** to every module-level helper in `dfm.py` (`InitCond,EMstep,em_converged,runKF,SKF,FIS,MissData`) and `news.py` (`para_const,News_DFM`): annotate args as `np.ndarray`/`dict`/`float` and returns as `dict`/`tuple[...]`/`np.ndarray`. Avoid blanket `# type: ignore` (it would itself error under `warn_unused_ignores`). Run `uv run mypy src/gdpnowcast/` → `Success`.
- [ ] **Step 3:** `just ci` (ruff+mypy+offline) green; `just test-golden` → all golden tests pass locally.
- [ ] **Step 4:** Update `RESUME.md`: **Phase 3 baseline-2017q1 COMPLETE** (golden frozen in 3a with `pickle_max_abs_dC=<value>`; ported DFM/news/runner reproduce it within `TOL`; estimator + news bugs fixed; offset removed; honest decomposition). **Explicitly note still-open:** fiscal variant + full multi-quarter backtest config (Phase 4), `pca(GDPC1)` BEA test (Phase 4).
- [ ] **Step 5:** `git add justfile RESUME.md && git commit -m "chore(phase3): golden test lane; type helpers; Phase 3 (baseline 2017q1) exit" && git push origin refactor/v2`.

---

## Open decisions / flags

- **⚑ NumPy-2 strategy (judgment call applied — flag for override).** This plan shims `Functions/` (A0) so golden+port share NumPy 2.4.6 and 1e-6 parity is robust, rather than freezing under NumPy<2 (which risks cross-version EM drift). A2 measures the residual drift vs the NumPy<2 production pickle (`pickle_max_abs_dC`). If you'd rather keep `Functions/` byte-for-byte untouched, the alternative is to freeze under `uv run --with 'numpy<2' …` and accept (and measure) the cross-version gap when the NumPy-2 port is checked against it.
- **⚑ Data panel (Phase 4, not here).** Golden parity runs on `data/US_*_v1` (the v1 panel) so it's unaffected by Phase 2's finding that v2 carries more early history + fixes a v1 quarterly stamping quirk. When Phase 4 reruns on the v2 panel, decide: truncate v2 to v1 series starts vs keep the fuller panel.
- **`gdp_actual` source.** The 18 scripts hardcode advance-estimate GDP. Phase 4 should source it point-in-time; Phase 3 keeps `cfg.gdp_actual` (golden parity needs v1's literal).
- **Fiscal variant + full backtest.** Only baseline `2017q1` is wired here (to prove the machinery). The runner is variant-agnostic (`data_subdir`/`spec_file` args); add a fiscal golden + the remaining `CONFIG_*` quarters in Phase 4.
- **`extract_common_residual` depth.** B6 ships the honest *projection* residual; the genuine state-based idiosyncratic decomposition is a Phase 7 deliverable.

## Self-review (author)

- **Spec coverage vs design §3 Phase-3 exit:** golden + SHA/version sidecar ✓ (A1–A4); `pytest -m golden` on migrated model ✓ (B4/B5/B7); parameterised `nowcast/runner.py` ✓ (B7); `mypy src/gdpnowcast/` clean ✓ (B8, with honest typing budget); three v1 bugs ✓ (B4 print/max_iter, B2 ValueErrors, B6 resid=0); MATLAB offset removed ✓ (B2/B5). New prerequisite A0 (NumPy-2) added — the design doc predates the NumPy-2 lock.
- **Corrections from independent review (verified 2026-06-01):** spec is 28 series / 2 quarterly (not 32/3); v1 crashes on NumPy 2.4.6 (`np.in1d`, `(1,1)`→scalar) → A0; v1 production params use `sample_start=2000-01-01` → freeze + parity pass it, and A2 checks the result against the committed pickle; `News_DFM` needs `para_const` → B5 ports it; `DfmSpec` now carries `units/category/units_transformed` so `verbose=True` works; B6 test made non-tautological; `update_nowcast` date-typed return documented; `time.append` not `np.hstack`; `x_sm` golden strengthened with a pinned GDP tail; mypy effort called out honestly.
- **Confirmed clean by review (don't re-investigate):** transform slice arithmetic matches v1 exactly; offset removal is numerically safe (all vintage dates month-start); no import cycle (`news/decomposition → dfm → _dfm_support`); OneDrive mitigated by `link-mode=copy`; first-pair `v_old` logic consistent A3↔B5↔B7; `max_iter` fix is a golden no-op.
- **Type/name consistency:** `load_dfm_spec`/`DfmSpec` (aliases incl. `UnitsTransformed`) → used by `load_vintage` (B2), `dfm` (B4), `update_nowcast` (B5), `gdp_common_share` (B6), `run_quarter` (B7). `SAMPLE_START=2000-01-01` applied for params in A1/A3/B4/B5/B7 and omitted for the news step everywhere (the v1 asymmetry). Return keys consistent A3↔B5↔B7.
