# Phase 3 Implementation Plan — Library migration + golden tests (de-MATLAB the DFM)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v1 MATLAB-style DFM pipeline (`Functions/` + `DFM_*.py` + `nowcast_*.py`) into a typed, tested `src/gdpnowcast/` library that reproduces v1's numbers bit-for-bit (proven by a frozen golden baseline), fixes the known v1 bugs, removes the MATLAB date offset, and replaces the 18 per-year backtest scripts with one parameterised runner.

**Architecture:** Two gated parts. **3a (hard gate):** run the *unmodified* v1 code on the *v1 data backup* (`data/US_*_v1/`) and freeze its outputs to `tests/golden/*.json` (+ a sidecar with the generating commit SHA and numpy/scipy versions). **3b:** port each module into `src/gdpnowcast/`, asserting golden parity at every step; no 3b edit happens before the 3a golden is committed. The ported pipeline is verified against the golden on the *same v1 data*, so port-correctness (3b) is cleanly separated from the data-panel differences found in Phase 2 (those are a Phase 4 concern — see "Open decisions").

**Tech Stack:** Python 3.13, numpy, scipy (`scipy.linalg.eig`, `block_diag`), pandas, pytest (`-m golden`), mypy (`disallow_untyped_defs`), ruff, `just`.

---

## Context & key findings (read before starting)

The v1 pipeline, traced end-to-end:

1. **`load_spec(path)`** (`Functions/load_spec.py`, a *class*) parses `Spec_US_new.xlsx` / `Spec_US_fiscal.xlsx`: keeps `Model==1` rows, sorts by frequency (`d,w,m,q,sa,a`), and exposes numpy-array attributes `SeriesID, SeriesName, Frequency, Units, Transformation, Category, UnitsTransformed` **plus `Blocks` (N×nBlocks loading matrix) and `BlockNames`**. The DFM needs `Blocks`/`BlockNames`; the Phase-2 `src/gdpnowcast/data/spec.py::SeriesSpec` does **not** carry them → Phase 3 adds a dedicated DFM spec loader.
2. **`load_data(datafile, Spec, sample=None)`** (`Functions/load_data.py`) reads a vintage `.xlsx` (raw values `Z`), reorders columns to `Spec.SeriesID`, **transforms** each series (`lin/chg/ch1/pch/pc1/pca/log`) to stationary `X`, drops the first quarter (`X[3:]`), and optionally drops rows before `sample`. `Time` is `Date.toordinal() + 366` (the MATLAB offset). The Phase-2 fetcher emits the *raw* vintage `.xlsx`; this transform layer lives in the model pipeline, so Phase 3 ports it.
3. **`dfm(X, Spec, threshold=1e-5, max_iter=5000)`** (`Functions/dfm.py`, 1086 ln) is the Banbura–Modugno EM/Kalman DFM. Returns `Res` with keys `x_sm, Z, C, R, A, Q, Mx, Wx, Z_0, V_0, r, p, loglik`. Helpers in the same file: `InitCond, EMstep, em_converged, runKF, SKF, FIS, MissData`. Support modules: `remNaNs_spline.py` (NaN handling), `decompose_common_factor.py`, `extract_common_residual.py`.
4. **`News_DFM(...)`** (`Functions/update_Nowcast.py`, 431 ln) computes the nowcast-news decomposition; **`update_nowcast2(X_old, X_new, Time, Spec, Res, series, period, vintage_old, vintage_new, display)`** (`Functions/update_Nowcast2.py`, thin wrapper) returns `{y_old, y_new, impact_revisions, impact_releases, news_table, ...}`. Both apply `+366`.
5. **`nowcast_<year>[_fiscal].py`** (18 scripts) drive the backtest: per quarter a hardcoded `vintages_dict`, a `param_map` (`prev`/`curr` ResDFM pickle + `switch_date` → "fixed within quarter, re-estimate at quarter start"), and hardcoded `gdp_adv_estimate` actuals. They loop consecutive vintage pairs through `update_nowcast2`, then write `nowcast_Q/`, `metrics_Q/`, `news_Q/`. **The `param_map` paths are absolute and broken** (`C:\...\Nova SBE\...\DFM_quarter_param\ResDFM_*.pickle`); the pickles themselves exist locally under `DFM_quarter_param/` (35) and `DFM_quarter_param_fiscal/` (35).

**Bugs to fix in 3b (from the audit + this read):**
- `Functions/dfm.py:786` — `print('...{} to {}').format(prev,loglik)` calls `.format` on `print()`'s `None` return → `AttributeError` whenever the log-likelihood decreases. Fix: `print('...{} to {}'.format(prev, loglik))`.
- `Functions/dfm.py:124` — `max_iter = 5000` reassigns and ignores the `max_iter` argument. Fix: delete the reassignment.
- **Unraised `ValueError`s**: `load_data.py:38` (`ValueError("File is not an EXCEL FILE")`), `load_data.py:148` (unknown transformation) and the dead `formula_dict["lin"]=lambda x:x*2` landmine (never hit because the `if formula=='lin'` branch uses identity — drop it). `load_spec.py:68` has malformed error text.
- **`extract_common_residual.py`** — `gdp_resid` hardcoded to `0.0` so `share_common` is always 1.0/NaN; the decomposition is meaningless. Fix: compute the idiosyncratic residual (observed minus common projection) properly.
- **MATLAB `+366`/`-366` offset** in `load_data.readData`, `update_nowcast2`, and the drivers — remove from the public API; use real `pandas.Timestamp`/`date` internally.

**What is NOT in Phase 3** (per design doc): the `gdpnowcast run` **CLI wrapper** and the Streamlit dashboard are **Phase 5** (they wrap the Phase-3b runner). The 4 methodology fixes (MTSDS133FMS `ch1`, quarterly DM+HLN, etc.) are **Phase 4**. Physical deletion of v1 root files is **Phase 5b**.

## Target file structure (created in 3b)

```
src/gdpnowcast/
├── dfm_spec.py          # DfmSpec dataclass + load_dfm_spec() (Blocks-aware; faithful to v1 load_spec)
├── transform.py         # vintage .xlsx -> (X, Time, Z); port of load_data.py, offset removed, ValueErrors raised
├── dfm.py               # the DFM core (region-sectioned), port of Functions/dfm.py + bug fixes
├── news.py              # News_DFM + update_nowcast (port of update_Nowcast*.py, offset removed)
├── decomposition.py     # fixed common/idiosyncratic GDP decomposition (port of extract_common_residual)
└── nowcast/
    ├── __init__.py
    ├── config.py        # backtest config: per-(year,quarter) vintages, param_map, gdp_actuals (replaces the 18 scripts' literals)
    └── runner.py        # parameterised backtest loop -> nowcast/metrics/news frames

tests/
├── golden/
│   ├── dfm_legacy_estimator.json   # 3a: v1 dfm() outputs for 2 vintages + sidecar
│   └── dfm_legacy_nowcast.json     # 3a: v1 2017q1 nowcast outputs (y_old/y_new/impacts)
├── test_dfm_golden.py              # 3b: ported dfm() matches estimator golden
├── test_news_golden.py            # 3b: ported news matches nowcast golden
├── test_transform.py               # 3b: transform parity vs v1 load_data on a vintage
└── test_dfm_spec.py                # 3b: spec loader (Blocks parsed)
```

---

# PART A — Phase 3a (HARD GATE: freeze the golden, then stop)

> No `src/gdpnowcast/` model code is written until Part A is committed. Part A only *reads* v1 code and *writes* JSON goldens + a one-off freeze script under `tools/`.

### Task A1: Golden-freeze harness for the DFM estimator

**Files:**
- Create: `tools/freeze_golden.py`
- Create: `tests/golden/` (dir; add `tests/golden/.gitkeep`)

- [ ] **Step 1: Create the freeze script that runs UNMODIFIED v1 `dfm()` on v1 data**

`tools/freeze_golden.py`:
```python
"""Phase 3a: freeze the v1 DFM estimator golden by running the UNMODIFIED v1
code (Functions/) on the v1 data backup (data/US_new_v1/). Run once; commit the
JSON. Do NOT edit Functions/ before this is committed.

Usage:  uv run python tools/freeze_golden.py
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import scipy

from Functions.dfm import dfm
from Functions.load_data import load_data
from Functions.load_spec import load_spec

REPO = Path(__file__).resolve().parents[1]
SAMPLE_START = None  # full sample (matches nowcast_*.py, which calls load_data w/o sample)
THRESHOLD = 1e-4     # matches DFM_new.py
# Two quarter-start vintages: they double as the prev/curr params for the 2017q1
# nowcast golden in Task A3.
VINTAGES = ["2016-10-03", "2017-01-03"]


def _digest(a: np.ndarray) -> dict:
    arr = np.asarray(a, dtype=float)
    return {
        "shape": list(arr.shape),
        "nansum": float(np.nansum(arr)),
        "nansumsq": float(np.nansum(arr**2)),
    }


def freeze(country: str, spec_file: str, out: Path) -> None:
    spec = load_spec(spec_file)
    vint_dir = REPO / "data" / f"{country}_v1"
    payload: dict = {"meta": {}, "vintages": {}, "params_pickle": {}}
    for v in VINTAGES:
        datafile = str(vint_dir / f"{v}.xlsx")
        X, Time, Z = load_data(datafile, spec)          # NOTE: no sample arg, like nowcast_*.py
        Res = dfm(X, spec, THRESHOLD)
        payload["vintages"][v] = {
            "X_shape": list(np.asarray(X).shape),
            "loglik_final": float(Res["loglik"][-1]),
            "C": np.asarray(Res["C"]).tolist(),
            "A": np.asarray(Res["A"]).tolist(),
            "Q": np.asarray(Res["Q"]).tolist(),
            "R": np.asarray(Res["R"]).tolist(),
            "Z_0": np.asarray(Res["Z_0"]).tolist(),
            "V_0": np.asarray(Res["V_0"]).tolist(),
            "Mx": np.asarray(Res["Mx"]).tolist(),
            "Wx": np.asarray(Res["Wx"]).tolist(),
            "x_sm_digest": _digest(Res["x_sm"]),
            "Z_digest": _digest(Res["Z"]),
        }
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
    payload["meta"] = {
        "v1_commit": sha,
        "data_source": f"data/{country}_v1",
        "threshold": THRESHOLD,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "python": platform.python_version(),
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(VINTAGES)} vintages)")


if __name__ == "__main__":
    freeze("US_new", "Spec_US_new.xlsx", REPO / "tests" / "golden" / "dfm_legacy_estimator.json")
```

- [ ] **Step 2: Create the golden dir marker**

Run: `New-Item -ItemType File tests/golden/.gitkeep` (PowerShell) — ensures the dir exists before the script writes.

- [ ] **Step 3: Commit the harness (no golden yet)**

```bash
git add tools/freeze_golden.py tests/golden/.gitkeep
git commit -m "test(phase3a): golden-freeze harness for the v1 DFM estimator"
```

### Task A2: Generate + commit the estimator golden

**Files:**
- Create: `tests/golden/dfm_legacy_estimator.json` (generated)

- [ ] **Step 1: Run the freeze script**

Run: `uv run python tools/freeze_golden.py`
Expected: prints `wrote tests/golden/dfm_legacy_estimator.json (2 vintages)`. Runtime ~1–3 min (two EM runs; ignore v1's verbose `print` output).

- [ ] **Step 2: Sanity-check the golden is non-degenerate**

Run:
```bash
uv run python -c "import json; d=json.load(open('tests/golden/dfm_legacy_estimator.json')); v=d['vintages']['2016-10-03']; print('loglik', v['loglik_final'], 'C shape', len(v['C']), len(v['C'][0]))"
```
Expected: a finite negative `loglik`, `C` shape `[32, k]` with `k` a multiple of 5 (block loadings). FAIL → investigate before committing.

- [ ] **Step 3: Commit the estimator golden**

```bash
git add tests/golden/dfm_legacy_estimator.json
git commit -m "test(phase3a): freeze v1 DFM estimator golden (2 vintages, v1 data)"
```

### Task A3: Generate + commit the end-to-end nowcast golden (2017q1)

**Files:**
- Create: `tools/freeze_golden_nowcast.py`
- Create: `tests/golden/dfm_legacy_nowcast.json` (generated)

- [ ] **Step 1: Create the nowcast freeze script (UNMODIFIED v1 news on v1 data)**

`tools/freeze_golden_nowcast.py`:
```python
"""Phase 3a: freeze the v1 end-to-end nowcast golden for 2017q1 by running the
UNMODIFIED v1 update_nowcast2 on the v1 data backup. Uses the two ResDFM params
re-estimated in Task A2's run (regenerated here for self-containment).

Usage:  uv run python tools/freeze_golden_nowcast.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from Functions.dfm import dfm
from Functions.load_data import load_data
from Functions.load_spec import load_spec
from Functions.update_Nowcast2 import update_nowcast2

REPO = Path(__file__).resolve().parents[1]
THRESHOLD = 1e-4
SERIES = "GDPC1"
PERIOD = "2017q1"
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
    # Re-estimate prev/curr params on v1 data (self-contained, reproducible).
    Xp, _, _ = load_data(vfile("2016-10-03"), spec)
    Res_prev = dfm(Xp, spec, THRESHOLD)
    Xc, _, _ = load_data(vfile("2017-01-03"), spec)
    Res_curr = dfm(Xc, spec, THRESHOLD)

    rows = []
    for i in range(1, len(VINTAGES)):
        v_old, v_new = VINTAGES[i - 1], VINTAGES[i]
        Res_use = Res_prev if np.datetime64(v_new) < SWITCH else Res_curr
        X_old, _, _ = load_data(vfile(v_old), spec)
        X_new, Time, _ = load_data(vfile(v_new), spec)
        r = update_nowcast2(X_old, X_new, Time, spec, Res_use, SERIES, PERIOD,
                            v_old, v_new, display=False)
        rows.append({
            "vintage": v_new,
            "y_old": float(r["y_old"][0]),
            "y_new": float(r["y_new"][0]),
            "impact_revisions": float(r["impact_revisions"][0]),
            "impact_releases": float(np.nansum(r["impact_releases"])),
        })
    out = REPO / "tests" / "golden" / "dfm_legacy_nowcast.json"
    out.write_text(json.dumps({"period": PERIOD, "series": SERIES, "rows": rows}, indent=2),
                   encoding="utf-8")
    print(f"wrote {out} ({len(rows)} vintage pairs)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run python tools/freeze_golden_nowcast.py`
Expected: `wrote tests/golden/dfm_legacy_nowcast.json (21 vintage pairs)`. Each row has finite `y_old`/`y_new` near the 2017q1 advance estimate (0.7) order of magnitude.

- [ ] **Step 3: Commit the nowcast golden + harness**

```bash
git add tools/freeze_golden_nowcast.py tests/golden/dfm_legacy_nowcast.json
git commit -m "test(phase3a): freeze v1 2017q1 nowcast golden (y_old/y_new/impacts, v1 data)"
```

### Task A4: Mark the 3a gate

- [ ] **Step 1: Record the gate in RESUME.md**

Add under the Phase-2 block in `RESUME.md`:
```markdown
**✅ Phase 3a gate (golden frozen).** `tests/golden/dfm_legacy_estimator.json` (2 vintages) + `dfm_legacy_nowcast.json` (2017q1) frozen from UNMODIFIED v1 code on v1 data; sidecar records the commit SHA + numpy/scipy versions. No de-MATLAB edit precedes this commit. 3b must reproduce these within tol.
```

- [ ] **Step 2: Commit**

```bash
git add RESUME.md && git commit -m "docs(phase3a): record golden-baseline gate"
```

> **GATE:** Part B begins only after A1–A4 are committed.

---

# PART B — Phase 3b (de-MATLAB port + runner)

### Task B1: DFM spec loader (Blocks-aware)

**Files:**
- Create: `src/gdpnowcast/dfm_spec.py`
- Test: `tests/test_dfm_spec.py`

- [ ] **Step 1: Write the failing test**

`tests/test_dfm_spec.py`:
```python
from gdpnowcast.dfm_spec import load_dfm_spec


def test_spec_has_blocks_and_quarterly_count() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    assert len(spec.series_id) == 32
    assert spec.blocks.shape[0] == 32          # one row per series
    assert (spec.blocks[:, 0] == 1).all()      # all load on the global block
    assert (spec.frequency == "q").sum() == 4  # GDPC1, ULCNFB, A261RX1Q020SBEA, GCEC1? (baseline: 3 q)
```
> Adjust the quarterly count to the baseline spec (baseline has 3 quarterly: GDPC1, ULCNFB, A261RX1Q020SBEA — `GCEC1` is fiscal-only). Verify against `Spec_US_new.xlsx` when writing.

- [ ] **Step 2: Run it — expect ImportError**

Run: `uv run pytest tests/test_dfm_spec.py -v` → FAIL (`ModuleNotFoundError: gdpnowcast.dfm_spec`).

- [ ] **Step 3: Implement `load_dfm_spec`** (faithful port of `Functions/load_spec.py`, typed, no print side-effect)

`src/gdpnowcast/dfm_spec.py`:
```python
"""Blocks-aware DFM spec loader — typed port of Functions/load_spec.py.
Separate from data/spec.py (the fetcher spec) because the DFM needs the
block-loading matrix and frequency-sorted numpy arrays."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

_FREQ_ORDER = ["d", "w", "m", "q", "sa", "a"]
_FIELDS = ["SeriesID", "SeriesName", "Frequency", "Units", "Transformation", "Category"]


@dataclass(frozen=True)
class DfmSpec:
    series_id: np.ndarray
    series_name: np.ndarray
    frequency: np.ndarray
    units: np.ndarray
    transformation: np.ndarray
    category: np.ndarray
    blocks: np.ndarray
    block_names: list[str]

    # v1-compatible attribute aliases (the ported dfm.py reads Spec.Blocks etc.)
    @property
    def Blocks(self) -> np.ndarray:  # noqa: N802
        return self.blocks

    @property
    def SeriesID(self) -> np.ndarray:  # noqa: N802
        return self.series_id

    @property
    def Frequency(self) -> np.ndarray:  # noqa: N802
        return self.frequency

    @property
    def SeriesName(self) -> np.ndarray:  # noqa: N802
        return self.series_name

    @property
    def BlockNames(self) -> list[str]:  # noqa: N802
        return self.block_names

    @property
    def Transformation(self) -> np.ndarray:  # noqa: N802
        return self.transformation


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

    return DfmSpec(
        series_id=raw["SeriesID"].to_numpy(copy=True),
        series_name=raw["SeriesName"].to_numpy(copy=True),
        frequency=raw["Frequency"].to_numpy(copy=True),
        units=raw["Units"].to_numpy(copy=True),
        transformation=raw["Transformation"].to_numpy(copy=True),
        category=raw["Category"].to_numpy(copy=True),
        blocks=blocks.to_numpy(copy=True),
        block_names=[re.sub("Block[0-9]+-", "", c) for c in block_cols],
    )
```

- [ ] **Step 4: Run the test — expect PASS**

Run: `uv run pytest tests/test_dfm_spec.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/dfm_spec.py tests/test_dfm_spec.py
git commit -m "feat(dfm): Blocks-aware DfmSpec loader (typed port of load_spec)"
```

### Task B2: Data transform (vintage .xlsx → X), offset removed, ValueErrors raised

**Files:**
- Create: `src/gdpnowcast/transform.py`
- Test: `tests/test_transform.py`

- [ ] **Step 1: Write the failing parity test (vs v1 `load_data`)**

`tests/test_transform.py`:
```python
import numpy as np

from Functions.load_data import load_data as v1_load_data
from Functions.load_spec import load_spec as v1_load_spec
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

VINT = "data/US_new_v1/2017-01-03.xlsx"


def test_transform_matches_v1_X() -> None:
    spec_v1 = v1_load_spec("Spec_US_new.xlsx")
    X1, T1, Z1 = v1_load_data(VINT, spec_v1)
    X2, T2, Z2 = load_vintage(VINT, load_dfm_spec("Spec_US_new.xlsx"))
    # X (the only thing the DFM consumes) must match exactly; NaNs in same places.
    assert X1.shape == X2.shape
    assert np.array_equal(np.isnan(X1), np.isnan(X2))
    np.testing.assert_allclose(np.nan_to_num(X1), np.nan_to_num(X2), rtol=0, atol=0)
```

- [ ] **Step 2: Run it — expect ImportError**

Run: `uv run pytest tests/test_transform.py -v` → FAIL.

- [ ] **Step 3: Implement `transform.py`** (port `Functions/load_data.py`; **remove `+366`** — return `Time` as a `pandas.DatetimeIndex`; **raise** the ValueErrors; drop the `lin:x*2` dead lambda)

`src/gdpnowcast/transform.py`:
```python
"""Vintage .xlsx -> (X transformed, Time, Z raw) for the DFM.
Typed port of Functions/load_data.py: MATLAB +366 offset removed (Time is a
real DatetimeIndex), unraised ValueErrors fixed, dead `lin:x*2` lambda dropped.
Numerically identical to v1 on X (proven by tests/test_transform.py)."""
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
    z = dat[mnem].to_numpy(copy=True)
    time = pd.DatetimeIndex(pd.to_datetime(dat["Date"]))
    return z, time, mnem


def _sort(z: np.ndarray, mnem: np.ndarray, spec: DfmSpec) -> np.ndarray:
    in_spec = np.in1d(mnem, spec.series_id)
    mnem, z = mnem[in_spec], z[:, in_spec]
    perm = np.array([np.where(mnem == s)[0][0] for s in spec.series_id])
    return z[:, perm]


def _transform(z: np.ndarray, spec: DfmSpec) -> np.ndarray:
    t, n = z.shape
    x = np.full((t, n), np.nan)
    for i in range(n):
        formula = spec.transformation[i]
        step = _FREQ_STEP[spec.frequency[i]]
        t1 = step - 1
        years = step / 12
        col = z[:, i].copy()
        if formula == "lin":
            x[:, i] = col
        elif formula == "chg":
            x[t1::step, i] = np.append(np.nan, col[t1 + step::step] - col[t1:-1 - t1:step])
        elif formula == "ch1":
            x[12 + t1::step, i] = col[12 + t1::step] - col[t1:-12:step]
        elif formula == "pch":
            x[t1::step, i] = (np.append(np.nan, col[t1 + step::step] / col[t1:-1 - t1:step]) - 1) * 100
        elif formula == "pc1":
            x[12 + t1::step, i] = ((col[12 + t1::step] / col[t1:-12:step]) - 1) * 100
        elif formula == "pca":
            x[t1::step, i] = (np.append(np.nan, col[t1 + step::step] / col[t1:-step:step]) ** (1 / years) - 1) * 100
        elif formula == "log":
            x[:, i] = np.log(col)
        else:
            raise ValueError(f"{formula}: transformation is unknown")
    return x


def load_vintage(
    datafile: str, spec: DfmSpec, sample_start: pd.Timestamp | None = None
) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    z, time, mnem = _read(datafile)
    z = _sort(z, mnem, spec)
    x = _transform(z, spec)
    x, time, z = x[3:, :], time[3:], z[3:, :]  # drop first quarter (transforms create NaNs)
    if sample_start is not None:
        keep = time >= sample_start
        x, time, z = x[keep, :], time[keep], z[keep, :]
    return x, time, z
```

- [ ] **Step 4: Run the parity test — expect PASS**

Run: `uv run pytest tests/test_transform.py -v` → PASS (X identical to v1, NaN masks identical).

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/transform.py tests/test_transform.py
git commit -m "feat(dfm): vintage transform (port of load_data); offset removed, ValueErrors raised"
```

### Task B3: Port the DFM support modules (remNaNs_spline, decompose_common_factor)

**Files:**
- Create: `src/gdpnowcast/_dfm_support.py` (holds `rem_nans_spline`, `decompose_common_factor`)
- Test: `tests/test_dfm_support.py`

- [ ] **Step 1: Write a parity test for `rem_nans_spline`**

`tests/test_dfm_support.py`:
```python
import numpy as np

from Functions.remNaNs_spline import remNaNs_spline as v1_rem
from gdpnowcast._dfm_support import rem_nans_spline


def test_rem_nans_spline_matches_v1() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal((60, 5))
    x[::7, 0] = np.nan
    x[:3, 1] = np.nan
    opt = {"method": 2, "k": 3}
    a1, b1 = v1_rem(x.copy(), opt)
    a2, b2 = rem_nans_spline(x.copy(), opt)
    np.testing.assert_allclose(np.nan_to_num(a1), np.nan_to_num(a2), rtol=0, atol=1e-12)
    np.testing.assert_array_equal(b1, b2)
```

- [ ] **Step 2: Run it — expect ImportError → FAIL**

Run: `uv run pytest tests/test_dfm_support.py -v`

- [ ] **Step 3: Port the two modules verbatim into `_dfm_support.py`**, renaming `remNaNs_spline`→`rem_nans_spline`, fixing imports to `from __future__ import annotations` + numpy, and adding type hints to the public signatures. Copy the bodies of `Functions/remNaNs_spline.py` and `Functions/decompose_common_factor.py` unchanged (same numpy ops) so behaviour is identical.

- [ ] **Step 4: Run the test — expect PASS**

Run: `uv run pytest tests/test_dfm_support.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/_dfm_support.py tests/test_dfm_support.py
git commit -m "feat(dfm): port remNaNs_spline + decompose_common_factor (parity-tested)"
```

### Task B4: Port the DFM core + fix the 3 estimator bugs (golden parity)

**Files:**
- Create: `src/gdpnowcast/dfm.py`
- Test: `tests/test_dfm_golden.py`

- [ ] **Step 1: Write the golden parity test**

`tests/test_dfm_golden.py`:
```python
import json
from pathlib import Path

import numpy as np
import pytest

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_estimator.json").read_text())
pytestmark = pytest.mark.golden


@pytest.mark.parametrize("vintage", list(GOLDEN["vintages"]))
def test_dfm_matches_legacy_golden(vintage: str) -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    x, _, _ = load_vintage(f"data/US_new_v1/{vintage}.xlsx", spec)
    res = dfm(x, spec, GOLDEN["meta"]["threshold"])
    g = GOLDEN["vintages"][vintage]
    assert res["loglik"][-1] == pytest.approx(g["loglik_final"], rel=1e-6, abs=1e-6)
    for key in ("C", "A", "Q", "R", "Z_0", "V_0", "Mx", "Wx"):
        np.testing.assert_allclose(np.asarray(res[key]), np.asarray(g[key]), rtol=1e-6, atol=1e-6)
    assert float(np.nansum(res["x_sm"])) == pytest.approx(g["x_sm_digest"]["nansum"], rel=1e-6)
```

- [ ] **Step 2: Run it — expect ImportError → FAIL**

Run: `uv run pytest -m golden tests/test_dfm_golden.py -v`

- [ ] **Step 3: Create `src/gdpnowcast/dfm.py` by copying `Functions/dfm.py` verbatim, then apply exactly these edits:**

  1. Imports: `from __future__ import annotations`; `from ._dfm_support import rem_nans_spline`; keep `from scipy.linalg import eig, block_diag`. Replace `remNaNs_spline(` calls with `rem_nans_spline(`.
  2. Delete the duplicate `max_iter = 5000` at the body line (was `dfm.py:124`) so the function argument is honoured.
  3. Fix `em_converged` (was `dfm.py:786`):
     ```python
     print("******likelihood decreased from {} to {}".format(previous_loglik, loglik))
     ```
  4. In `InitCond`, replace the bare `except ValueError:` blocks (was `dfm.py:390,395`) so they re-raise unless they are the intended singular-matrix fallback — keep the existing fallback behaviour but add a comment; do NOT change the numerical path.
  5. Wrap module side-effect `print(...)` calls (the "Table 3" / "Estimating..." prints) behind an optional `verbose: bool = False` parameter on `dfm(...)` defaulting to `False` (silences the port; v1 printed unconditionally — output-only change, no numerics).
  6. Add type hints to `dfm`'s signature: `def dfm(X: np.ndarray, spec: DfmSpec, threshold: float = 1e-5, max_iter: int = 5000, verbose: bool = False) -> dict:` (internal helpers may stay loosely typed; `# type: ignore[no-untyped-def]` only if mypy forces it — prefer real hints).

  Add `# region:` section markers around the major blocks (`dfm`, `InitCond`, `EMstep`, Kalman `runKF/SKF/FIS/MissData`) per the design doc.

- [ ] **Step 4: Run the golden test — expect PASS (both vintages)**

Run: `uv run pytest -m golden tests/test_dfm_golden.py -v`
Expected: 2 passed. If a matrix mismatches: the port changed a numerical op — diff against `Functions/dfm.py` line-by-line; do NOT loosen tolerance to hide it.

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/dfm.py tests/test_dfm_golden.py
git commit -m "feat(dfm): port DFM core (de-MATLAB); fix print bug + max_iter; golden parity"
```

### Task B5: Port the news module (News_DFM + update_nowcast), offset removed (golden parity)

**Files:**
- Create: `src/gdpnowcast/news.py`
- Test: `tests/test_news_golden.py`

- [ ] **Step 1: Write the nowcast golden parity test**

`tests/test_news_golden.py`:
```python
import json
from pathlib import Path

import numpy as np
import pytest

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.news import update_nowcast
from gdpnowcast.transform import load_vintage

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_nowcast.json").read_text())
pytestmark = pytest.mark.golden
SWITCH = np.datetime64("2017-01-01")


def _vfile(v: str) -> str:
    return f"data/US_new_v1/{v}.xlsx"


def test_news_matches_legacy_nowcast_golden() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    xp, _, _ = load_vintage(_vfile("2016-10-03"), spec)
    res_prev = dfm(xp, spec, 1e-4)
    xc, _, _ = load_vintage(_vfile("2017-01-03"), spec)
    res_curr = dfm(xc, spec, 1e-4)
    for row in GOLDEN["rows"]:
        v_new = row["vintage"]
        # consecutive pair: find v_old = the row before in the golden order
        idx = [r["vintage"] for r in GOLDEN["rows"]].index(v_new)
        v_old = "2016-12-02" if idx == 0 else GOLDEN["rows"][idx - 1]["vintage"]
        res_use = res_prev if np.datetime64(v_new) < SWITCH else res_curr
        x_old, _, _ = load_vintage(_vfile(v_old), spec)
        x_new, time, _ = load_vintage(_vfile(v_new), spec)
        out = update_nowcast(x_old, x_new, time, spec, res_use, "GDPC1", "2017q1",
                             v_old, v_new)
        assert float(out["y_new"][0]) == pytest.approx(row["y_new"], rel=1e-6, abs=1e-6)
        assert float(out["y_old"][0]) == pytest.approx(row["y_old"], rel=1e-6, abs=1e-6)
```
> Note: the first row's `v_old` is fixed to `2016-12-02` per the v1 loop (`range(1, len(vintages))` starts the pair list at `vintages[0]`); align this with how A3 built the golden.

- [ ] **Step 2: Run it — expect ImportError → FAIL**

Run: `uv run pytest -m golden tests/test_news_golden.py -v`

- [ ] **Step 3: Port `News_DFM` (from `Functions/update_Nowcast.py`) and `update_nowcast` (from `update_Nowcast2.py`) into `src/gdpnowcast/news.py`**, applying:
  1. Copy `News_DFM` body verbatim (uses `SKF`, `FIS` — import `from .dfm import SKF, FIS`). Add type hints to the public signature.
  2. Rewrite `update_nowcast` to take `Time` as a `pandas.DatetimeIndex` (no `+366`): replace `dt.strptime(...).toordinal()+366` with `pd.Timestamp(...)`, replace the `future` ordinal math with `time[-1] + pd.offsets.MonthBegin(i)` (12 months), and the `t_nowcast = np.where((dt(y,m,d).toordinal()+366)==Time)` lookups with `np.where(time == pd.Timestamp(y, m, 1))`. Keep the `X_old`/`X_new` padding (12 NaN rows) and the `News_DFM` calls unchanged.
  3. Drop the `display` print block to a `verbose: bool = False` flag (output-only).
  4. Keep the return dict keys identical (`y_old, y_new, impact_revisions, impact_releases, news_table, vintage_old, vintage_new`).

- [ ] **Step 4: Run the golden test — expect PASS**

Run: `uv run pytest -m golden tests/test_news_golden.py -v`
Expected: 1 passed (all 21 pairs within tol). Mismatch → diff the date math; the offset change must not move `t_nowcast`.

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/news.py tests/test_news_golden.py
git commit -m "feat(dfm): port News_DFM + update_nowcast; remove MATLAB date offset; golden parity"
```

### Task B6: Fix `extract_common_residual` → proper common/idiosyncratic decomposition

**Files:**
- Create: `src/gdpnowcast/decomposition.py`
- Test: `tests/test_decomposition.py`

- [ ] **Step 1: Write the failing test (residual is NOT trivially zero)**

`tests/test_decomposition.py`:
```python
import numpy as np

from gdpnowcast.decomposition import gdp_common_idiosyncratic
from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage


def test_common_plus_idiosyncratic_equals_observed_where_observed() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    x, _, _ = load_vintage("data/US_new_v1/2017-01-03.xlsx", spec)
    res = dfm(x, spec, 1e-4)
    d = gdp_common_idiosyncratic(x, spec, res, series="GDPC1")
    # At the latest period where GDPC1 is observed, common + idiosyncratic == observed.
    assert np.isfinite(d["gdp_common"])
    assert d["gdp_idiosyncratic"] != 0.0           # the v1 bug hardcoded this to 0
    assert d["gdp_total"] == d["gdp_common"] + d["gdp_idiosyncratic"]
```

- [ ] **Step 2: Run it — expect ImportError → FAIL**

Run: `uv run pytest tests/test_decomposition.py -v`

- [ ] **Step 3: Implement `gdp_common_idiosyncratic`** — port `extract_common_residual.py`'s SKF call but compute the idiosyncratic part as `observed − common` (de-standardised), not `0.0`:

`src/gdpnowcast/decomposition.py`:
```python
"""GDP common/idiosyncratic decomposition — fixes Functions/extract_common_residual.py,
which hardcoded the residual to 0.0 (making share_common always 1.0)."""
from __future__ import annotations

import numpy as np

from .dfm import SKF
from .dfm_spec import DfmSpec


def gdp_common_idiosyncratic(
    x: np.ndarray, spec: DfmSpec, res: dict, series: str = "GDPC1"
) -> dict:
    n_model = res["C"].shape[0]
    xn = x.T if x.shape[0] != n_model else x  # (N, T)
    skf = SKF(xn, res["A"], res["C"], res["Q"], res["R"], res["Z_0"], res["V_0"])
    z = skf["Zm"]
    f_last = z[:, -1] if z.shape[0] <= z.shape[1] else z[-1, :]

    i = int(np.where(np.asarray(spec.series_id) == series)[0][0])
    wx, mx = res["Wx"][i], res["Mx"][i]
    common = float(np.dot(res["C"][i, :], f_last)) * wx + mx

    observed_std = xn[i, -1]                       # standardised observed (may be NaN)
    if np.isnan(observed_std):
        total, idio = common, 0.0                  # nothing observed -> all common (by construction)
    else:
        total = float(observed_std) * wx + mx
        idio = total - common
    return {
        "series": series,
        "gdp_total": total,
        "gdp_common": common,
        "gdp_idiosyncratic": idio,
        "share_common": np.nan if total == 0 else common / total,
    }
```
> The `total == common + idio` identity holds by construction; the point of the fix is that the idiosyncratic term is the real residual, not `0.0`.

- [ ] **Step 4: Run the test — expect PASS**

Run: `uv run pytest tests/test_decomposition.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/decomposition.py tests/test_decomposition.py
git commit -m "fix(dfm): real GDP common/idiosyncratic decomposition (was hardcoded resid=0)"
```

### Task B7: Parameterised backtest runner (deduplicate the 18 scripts)

**Files:**
- Create: `src/gdpnowcast/nowcast/__init__.py`, `src/gdpnowcast/nowcast/config.py`, `src/gdpnowcast/nowcast/runner.py`
- Test: `tests/test_runner_golden.py`

- [ ] **Step 1: Extract the backtest config into data, not code**

`src/gdpnowcast/nowcast/config.py` — define typed structures and **port the literals** from the 18 `nowcast_*.py` scripts (vintages per quarter, `gdp_adv_estimate` actuals, and the `param_map` `prev`/`curr`/`switch_date` using **relative** `DFM_quarter_param/ResDFM_*.pickle` paths). Provide at minimum the `2017q1` entry needed for the golden:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuarterCfg:
    period: str                 # e.g. "2017q1"
    vintages: list[str]
    gdp_actual: float
    prev_vintage: str           # quarter-start vintage whose Res params are "prev"
    curr_vintage: str           # quarter-start vintage whose Res params are "curr"
    switch_date: str            # ISO; >= switch -> use curr


# Ported from nowcast_2017.py (extend with the other years/quarters incrementally).
CONFIG_2017Q1 = QuarterCfg(
    period="2017q1",
    vintages=[
        "2016-12-02", "2016-12-09", "2016-12-16", "2016-12-23", "2016-12-30",
        "2017-01-06", "2017-01-13", "2017-01-20", "2017-01-27",
        "2017-02-03", "2017-02-10", "2017-02-17", "2017-02-24",
        "2017-03-03", "2017-03-10", "2017-03-17", "2017-03-24", "2017-03-31",
        "2017-04-07", "2017-04-14", "2017-04-21", "2017-04-28",
    ],
    gdp_actual=0.7,
    prev_vintage="2016-10-03",
    curr_vintage="2017-01-03",
    switch_date="2017-01-01",
)
```
> The runner estimates `prev`/`curr` params on the fly from `prev_vintage`/`curr_vintage` (no opaque pickles), so the broken absolute paths are gone entirely. (The on-disk `DFM_quarter_param/*.pickle` may be used later as a fast cache, but the runner does not depend on them.)

- [ ] **Step 2: Write the runner golden parity test**

`tests/test_runner_golden.py`:
```python
import json
from pathlib import Path

import pytest

from gdpnowcast.nowcast.config import CONFIG_2017Q1
from gdpnowcast.nowcast.runner import run_quarter

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_nowcast.json").read_text())
pytestmark = pytest.mark.golden


def test_runner_reproduces_2017q1_golden() -> None:
    df = run_quarter(CONFIG_2017Q1, country="US_new", data_subdir="US_new_v1",
                     spec_file="Spec_US_new.xlsx", series="GDPC1")
    got = {r["vintage"]: r for r in df.to_dict("records")}
    for row in GOLDEN["rows"]:
        assert got[row["vintage"]]["y_new"] == pytest.approx(row["y_new"], rel=1e-6, abs=1e-6)
```

- [ ] **Step 3: Run it — expect ImportError → FAIL**

Run: `uv run pytest -m golden tests/test_runner_golden.py -v`

- [ ] **Step 4: Implement `run_quarter`** in `src/gdpnowcast/nowcast/runner.py` — the deduplicated loop:
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


def _vfile(subdir: str, v: str) -> str:
    return str(_REPO / "data" / subdir / f"{v}.xlsx")


def run_quarter(
    cfg: QuarterCfg, country: str, data_subdir: str, spec_file: str, series: str = "GDPC1"
) -> pd.DataFrame:
    spec = load_dfm_spec(spec_file)
    xp, _, _ = load_vintage(_vfile(data_subdir, cfg.prev_vintage), spec)
    res_prev = dfm(xp, spec, 1e-4)
    xc, _, _ = load_vintage(_vfile(data_subdir, cfg.curr_vintage), spec)
    res_curr = dfm(xc, spec, 1e-4)
    switch = np.datetime64(cfg.switch_date)

    rows = []
    for i in range(1, len(cfg.vintages)):
        v_old, v_new = cfg.vintages[i - 1], cfg.vintages[i]
        res_use = res_prev if np.datetime64(v_new) < switch else res_curr
        x_old, _, _ = load_vintage(_vfile(data_subdir, v_old), spec)
        x_new, time, _ = load_vintage(_vfile(data_subdir, v_new), spec)
        out = update_nowcast(x_old, x_new, time, spec, res_use, series, cfg.period, v_old, v_new)
        y_new = float(out["y_new"][0])
        rows.append({
            "vintage": v_new,
            "y_old": float(out["y_old"][0]),
            "y_new": y_new,
            "error": cfg.gdp_actual - y_new,
            "impact_revisions": float(out["impact_revisions"][0]),
            "impact_releases": float(np.nansum(out["impact_releases"])),
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 5: Run the golden test — expect PASS**

Run: `uv run pytest -m golden tests/test_runner_golden.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gdpnowcast/nowcast/ tests/test_runner_golden.py
git commit -m "feat(nowcast): parameterised backtest runner (dedupe 18 scripts); 2017q1 golden parity"
```

### Task B8: mypy clean + full CI + Phase-3 exit

**Files:**
- Modify: `justfile` (add `test-golden` lane), `RESUME.md`

- [ ] **Step 1: Add a golden test lane to the justfile**

In `justfile`, add:
```makefile
# golden parity tests (need data/US_new_v1 + tests/golden/*.json)
test-golden:
    uv run pytest -m golden -v
```
And ensure the default `test` lane still excludes slow/golden if golden needs the v1 backup: mark golden tests as already done via `pytestmark = pytest.mark.golden`; register the `golden` marker in `pyproject.toml` `[tool.pytest.ini_options].markers` (it already lists `golden`). Keep `just test` = `-m "not slow"` (golden runs in CI only if the v1 backup is present; otherwise skip via a guard).

- [ ] **Step 2: Guard golden tests when the v1 backup is absent (CI has no data/)**

Add to each golden test module top:
```python
import pytest
from pathlib import Path
pytestmark = [pytest.mark.golden,
             pytest.mark.skipif(not Path("data/US_new_v1").exists(),
                                reason="v1 data backup absent (local-only golden)")]
```

- [ ] **Step 3: Run mypy on the new modules**

Run: `uv run mypy src/gdpnowcast/`
Expected: `Success`. Fix any `no-untyped-def` in the new files (helpers in `dfm.py` may need `# type: ignore[no-untyped-def]` if a faithful port resists typing — prefer real hints; document any ignore).

- [ ] **Step 4: Run the full local suite (offline + golden)**

Run: `just ci` then `just test-golden`
Expected: `just ci` green (ruff+mypy+offline tests); `test-golden` → all golden tests pass locally.

- [ ] **Step 5: Update RESUME + commit**

Update `RESUME.md`: Phase 3 COMPLETE (golden frozen in 3a; ported DFM/news/runner reproduce it within 1e-6; 3 estimator/news bugs + decomposition fixed; offset removed). Note Phase 4 next.
```bash
git add justfile pyproject.toml RESUME.md
git commit -m "chore(phase3): golden test lane + CI guard; Phase 3 exit (de-MATLAB complete)"
git push origin refactor/v2
```

---

## Open decisions / flags

- **⚑ Data panel (deferred to Phase 4, NOT this plan).** Phase 2 found v2 carries ~194.5k cells more early history than v1 (`PCEC96` 1985 vs 2002; `DGORDER`/`BUSINV` 1985 vs 1992) and that v1 mis-stamps the quarterly series in ~10 year-end vintages. **Phase 3 golden parity deliberately runs on `data/US_*_v1` (the v1 panel)** so it is unaffected. When Phase 4 reruns the backtest on the v2 panel (`data/US_new`), decide: truncate v2 to v1's series starts (isolate methodology from data) vs keep the fuller panel. Document the chosen option and its effect on the headline.
- **`gdp_actual` source.** The 18 scripts hardcode advance-estimate GDP per quarter. Phase 4 should source these point-in-time (BEA advance release) rather than hardcoding; for Phase 3 the runner keeps the hardcoded `cfg.gdp_actual` (golden parity requires matching v1's literals).
- **Fiscal variant.** This plan parity-tests `US_new` (baseline). The fiscal variant reuses the same modules with `Spec_US_fiscal.xlsx` + `data/US_fiscal_v1`; add a fiscal golden + `CONFIG_*` entries when extending the backtest in Phase 4 (the runner is already variant-agnostic via its `country`/`spec_file` args).
- **Full backtest (all years/quarters).** Task B7 ports only `2017q1` config to prove the runner. The remaining 35 quarters' literals are mechanical to port from the 18 scripts; do them in Phase 4 (the full rerun) — or extend `config.py` now if you prefer a complete runner before Phase 4.

## Self-review (done by the author)

- **Spec coverage vs design doc §3 Phase 3 exit criteria:** 3a golden + SHA/version sidecar ✓ (A1–A4); `pytest -m golden` on migrated model ✓ (B4/B5/B7); parameterised `nowcast/runner.py` ✓ (B7); `mypy src/gdpnowcast/` clean ✓ (B8); three v1 bugs (`dfm.py:786`, unraised ValueErrors, broken `extract_common_residual`) ✓ (B4/B2/B6); MATLAB offset removed from public API ✓ (B2/B5).
- **Placeholder scan:** the only intentionally-partial item is the backtest config (2017q1 only) — explicitly flagged as a Phase-4 extension, not a hidden gap. The `freeze_golden_nowcast.py` `if False` line is called out for deletion.
- **Type/name consistency:** `load_dfm_spec`/`DfmSpec` (B1) used by `transform.load_vintage` (B2), `dfm` (B4), `news.update_nowcast` (B5), `runner.run_quarter` (B7); `DfmSpec` exposes v1-style `.Blocks/.SeriesID/.Frequency/...` aliases so the verbatim-ported `dfm.py`/`News_DFM` bodies keep working unedited. Return-dict keys (`y_old,y_new,impact_revisions,impact_releases,news_table`) consistent A3↔B5↔B7.
