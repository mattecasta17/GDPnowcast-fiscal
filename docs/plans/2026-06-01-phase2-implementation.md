# Phase 2 — ALFRED Vintage Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a NEW point-in-time ALFRED fetcher that rebuilds all 35 series into weekly + quarter-start vintage Excel files for both variants (baseline 32 / fiscal 35), reproducing v1's 485/486 vintage files with zero forward-looking-bias.

**Architecture:** For each series, fetch its full ALFRED release history once (`get_series_all_releases` → `[realtime_start, date, value]`); reconstruct each as-of vintage locally (for each observation date, the latest value whose `realtime_start <= D`). Quarterly series are shifted +2 months onto the last month of the quarter (v1 convention). A committed manifest of the real v1 vintage dates drives the loop (avoids the `fridays_between` bug that drops the 33 quarter-start vintages). The fetcher writes Excel vintage files matching v1's `load_data.readData` contract (a `Date` monthly column + one column per `SeriesID`).

**Tech Stack:** Python 3.13, `fredapi`, `pandas`, `python-dotenv`, `typer`, `pytest`. Package layout `src/gdpnowcast/data/`. Output to gitignored `data/US_new/` (baseline) and `data/US_fiscal/` (fiscal).

---

## Context the engineer needs (read first)

This plan was preceded by a **pre-Phase-2 ALFRED-coverage go/no-go spike** (`tools/alfred_coverage_spike.py`, ran 2026-06-01) which **PASSED GO 35/35**: every series resolves on FRED, returns a non-empty point-in-time as-of series, and has ALFRED vintage history back well before the first vintage 2016-10-03 (tightest = `MTSDS133FMS`, earliest vintage 2015-09-11). **No fallback branch is needed.**

Grounding facts established before writing this plan:

- **Series set** (`Spec_US_new.xlsx` = 32 baseline; `Spec_US_fiscal.xlsx` = 35 = the 32 + `GCEC1`, `MTSDS133FMS`, `W875RX1`). The fiscal spec is a strict superset. Sheet name is `spec`. Columns: `Model, SeriesID, SeriesName, Frequency, Block1-4, Transformation, Units, Category`.
- **4 quarterly series** (`Frequency == "q"`): `GDPC1`, `ULCNFB`, `A261RX1Q020SBEA`, `GCEC1`. All others are monthly (`"m"`).
- **Real v1 vintages on disk** (gitignored, present at execution time): `data/US_new/` = 486 files, `data/US_fiscal/` = 485 files, named `YYYY-MM-DD.xlsx`, range `2016-10-03 .. 2025-07-25`. Of the 485 fiscal dates, **33 are NOT Fridays** — they are the quarter-start re-estimation vintages (Jan/Apr/Jul/Oct 1-3). `data/US_new` has one extra vintage `2021-01-04` that `data/US_fiscal` lacks (a v1 inconsistency — see Decision D2).
- **Vintage file format** (the contract `Functions/load_data.py::readData` reads): first sheet has a `Date` column (monthly, `freq="MS"`, from `1985-01-01` to the month of the vintage) plus one column per `SeriesID`. Quarterly values are stamped on the **last month of the quarter** (Mar/Jun/Sep/Dec) — FRED returns them at quarter-start, so v1 shifts `+2` months. Missing as-of cells are left blank/NaN. Column order is cosmetic (the loader re-sorts by `Spec.SeriesID`).
- **Fetch primitive verified:** `fred.get_series_all_releases(sid)` returns object-dtype columns `[realtime_start, date, value]`; reconstructing as-of `D` locally (filter `realtime_start <= D`, take the latest value per `date`) reproduces `fred.get_series(sid, realtime_start=D, realtime_end=D)` **exactly** (checked on PPIFIS and GCEC1 at 2020-04-01). ~35 unique-series calls cover both variants — the "~32,000 call" per-vintage loop is unnecessary.
- **Env gotcha:** a stale Windows User env var can shadow `.env`. Always `load_dotenv(REPO_ROOT / ".env", override=True)` in `get_fred()`.
- **Tooling:** `just ci` = `lint typecheck test`. `ruff check src/ tests/` + `ruff format --check src/ tests/`; `mypy src/gdpnowcast/ tests/` (so **every test function needs `-> None`** and type hints — `disallow_untyped_defs=true`). `ruff`/`mypy` do NOT scan `tools/`. Tests run via `uv run pytest`. On Windows prefix shell commands with the PATH refresh (see napkin Tooling #2) — but the recipes call `uv run`, which is shell-agnostic.

---

## Decision points (confirm with Matteo BEFORE executing)

These were surfaced per Matteo's incremental-orchestration preference and **decided with him on 2026-06-01** (resolutions inline below).

- **D1 — Fetch strategy. ✅ DECIDED: local reconstruction.** Per-series full release history (`get_series_all_releases`) + local reconstruction (~35-67 calls, ~1-3 s each, verified identical to point-in-time). *Rejected alternative:* v1's per-vintage `get_series(realtime_start=D, realtime_end=D)` loop (~32k calls, hours, anticipated by design-doc §8). The reconstruction approach is **guarded by the Task 4 cross-validation test** that proves it equals the direct point-in-time API. This consciously supersedes the design-doc §8 "parallel per-vintage fetch + checkpoints" assumption.
- **D2 — The `2021-01-04` fiscal gap. ✅ DECIDED: complete the fiscal set to 486.** `data/US_new` (baseline) has `2021-01-04`; `data/US_fiscal` lacks it. We **add it to the fiscal manifest** so both variants share the full, correct canonical vintage set (486 each, identical date lists). Document in `data_sources.md` that v1's fiscal set was missing this quarter-start and that v2 completes it. Note for Phase 3a/4: the fiscal backtest now has one re-estimation vintage (`2021-01-04`) that v1's `Results.pdf` did not — call this out when comparing to v1 numbers (honest research).
- **D3 — Value reproduction expectation (honest-research framing). ✅ ACKNOWLEDGED.** The 3 fiscal series were fetched from ALFRED in v1 (`variables_creation.py`), so the new fetcher should match them closely. The 32 baseline series had **no v1 fetcher** — their v1 vintage files came from a different source (FRBNY pipeline), so byte-for-byte value matches are **not guaranteed**. Therefore: the **hard Phase 2 exit gate is the filename superset assertion**; the value comparison vs v1 files is a **diagnostic** (reported in `data_sources.md`), and any divergence is documented honestly, not suppressed (napkin User-Directive #3, [[feedback-honest-research]]).
- **Execution mode. ✅ DECIDED: inline, with a review checkpoint after each task** (`superpowers:executing-plans`).

---

## File structure

**Create:**
- `src/gdpnowcast/data/__init__.py` — package marker.
- `src/gdpnowcast/data/spec.py` — `SeriesSpec` dataclass + `load_spec()` + `SPEC_PATHS`.
- `src/gdpnowcast/data/vintages.py` — `load_manifest()` + date-rule helpers for validation.
- `src/gdpnowcast/data/fred.py` — `get_fred()`, `fetch_release_history()`, `reconstruct_asof()`, `asof_series()`.
- `src/gdpnowcast/data/builder.py` — `monthly_index()`, `build_vintage()`, `write_vintage()`.
- `src/gdpnowcast/cli.py` — Typer `app` + `fetch` command (the `pyproject` console-script target).
- `configs/vintages_baseline.csv`, `configs/vintages_fiscal.csv` — committed manifests.
- `tests/test_spec.py`, `tests/test_vintages.py`, `tests/test_reconstruction.py`, `tests/test_builder.py`, `tests/test_fetch_integration.py` (network, slow), `tests/test_superset.py`.
- `docs/data_sources.md`.
- `tools/make_vintage_manifest.py` — one-time manifest generator (dev tool, not in `src/`).

**Modify:**
- `justfile:33-35` — replace the `fetch` placeholder with the real CLI call.

**Read but do not move** (configs/ relocation is deferred to Phase 5b): root `Spec_US_new.xlsx`, `Spec_US_fiscal.xlsx`.

---

### Task 1: Vintage manifests (committed) + loader

**Files:**
- Create: `tools/make_vintage_manifest.py`
- Create: `configs/vintages_baseline.csv`, `configs/vintages_fiscal.csv`
- Create: `src/gdpnowcast/data/__init__.py`, `src/gdpnowcast/data/vintages.py`
- Test: `tests/test_vintages.py`

- [ ] **Step 1: Write the manifest generator** (`tools/make_vintage_manifest.py`)

```python
"""One-time dev tool: extract the real v1 vintage dates from data/US_*/ filenames
into committed manifests. Re-run only if the v1 vintage set on disk changes."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.xlsx$")
SOURCES = {"baseline": "US_new", "fiscal": "US_fiscal"}


def main() -> None:
    # D2: complete both variants to the canonical UNION of v1 vintage dates. v1's
    # fiscal set was missing 2021-01-04 (present in baseline); adding it gives both
    # variants the full, correct vintage set (486 each, identical date lists).
    found: dict[str, set[str]] = {}
    for variant, subdir in SOURCES.items():
        src = REPO_ROOT / "data" / subdir
        found[variant] = {
            m.group(1) for f in src.glob("*.xlsx") if (m := PATTERN.match(f.name))
        }
    canonical = sorted(found["baseline"] | found["fiscal"])
    for variant in SOURCES:
        out = REPO_ROOT / "configs" / f"vintages_{variant}.csv"
        out.write_text("vintage\n" + "\n".join(canonical) + "\n", encoding="utf-8")
        added = sorted(set(canonical) - found[variant])
        print(f"{variant}: {len(canonical)} vintages -> {out}  (added vs v1: {added})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it to generate the committed manifests**

Run: `uv run python tools/make_vintage_manifest.py`
Expected: `baseline: 486 vintages -> ...  (added vs v1: [])` and `fiscal: 486 vintages -> ...  (added vs v1: ['2021-01-04'])`. Both CSVs are now identical 486-date lists. Inspect the head: header `vintage`, then `2016-10-03`, `2016-12-07`, ...

- [ ] **Step 3: Write `vintages.py`**

```python
"""Vintage-date manifests. The manifest is the authoritative vintage list,
extracted from the real v1 files (tools/make_vintage_manifest.py). The Fridays/
quarter-start helpers exist only so a test can prove the manifest drops nothing
(the historical fridays_between bug omitted the 33 quarter-start re-estimation
vintages)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATHS = {
    "baseline": REPO_ROOT / "configs" / "vintages_baseline.csv",
    "fiscal": REPO_ROOT / "configs" / "vintages_fiscal.csv",
}


def load_manifest(variant: str) -> list[date]:
    df = pd.read_csv(MANIFEST_PATHS[variant], dtype={"vintage": str})
    return sorted(date.fromisoformat(s) for s in df["vintage"])


def fridays_between(start: date, end: date) -> list[date]:
    # pandas (typed) instead of dateutil.rrule, which ships no mypy stubs.
    return [d.date() for d in pd.date_range(start=start, end=end, freq="W-FRI")]
```

- [ ] **Step 4: Write the validation test** (`tests/test_vintages.py`)

```python
from datetime import date

from gdpnowcast.data.vintages import fridays_between, load_manifest


def test_manifest_counts() -> None:
    # D2: both variants completed to the canonical 486-date union.
    assert len(load_manifest("baseline")) == 486
    assert len(load_manifest("fiscal")) == 486


def test_both_manifests_identical() -> None:
    assert load_manifest("baseline") == load_manifest("fiscal")


def test_fiscal_completed_with_2021_01_04() -> None:
    # v1's fiscal set lacked this quarter-start; v2 adds it (Decision D2).
    assert date(2021, 1, 4) in load_manifest("fiscal")


def test_manifest_range() -> None:
    m = load_manifest("fiscal")
    assert m[0] == date(2016, 10, 3)
    assert m[-1] == date(2025, 7, 25)


def test_manifest_includes_all_quarter_starts() -> None:
    # The quarter-start re-estimation vintages must be present (the bug
    # fridays_between introduced dropped them). Every non-Friday date is one;
    # the canonical 486-set has 34 (33 from v1 fiscal + the added 2021-01-04).
    m = load_manifest("fiscal")
    non_fridays = [d for d in m if d.weekday() != 4]
    assert len(non_fridays) == 34
    assert date(2020, 4, 1) in m  # spot-check a known quarter-start


def test_manifest_drops_no_friday() -> None:
    # Every Friday in the covered range must be present (no weekly vintage dropped).
    m = set(load_manifest("fiscal"))
    fridays = set(fridays_between(min(m), max(m)))
    missing = sorted(fridays - m)
    # v1 may skip a handful of holiday Fridays; assert the manifest covers >= 95%.
    assert len(missing) <= 0.05 * len(fridays), f"too many missing Fridays: {missing}"
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_vintages.py -v`
Expected: PASS (6 tests). If `test_manifest_drops_no_friday` fails with many missing Fridays, investigate before relaxing — it means the manifest is Fridays-incomplete.

- [ ] **Step 6: Commit**

```bash
git add tools/make_vintage_manifest.py configs/vintages_baseline.csv configs/vintages_fiscal.csv src/gdpnowcast/data/__init__.py src/gdpnowcast/data/vintages.py tests/test_vintages.py
git commit -m "feat(phase2): commit v1 vintage manifests + loader with drop-nothing test"
```

---

### Task 2: Series spec loader

**Files:**
- Create: `src/gdpnowcast/data/spec.py`
- Test: `tests/test_spec.py`

- [ ] **Step 1: Write the failing test** (`tests/test_spec.py`)

```python
from gdpnowcast.data.spec import SPEC_PATHS, load_spec


def test_baseline_has_32_series() -> None:
    assert len(load_spec(SPEC_PATHS["baseline"])) == 32


def test_fiscal_is_superset_of_baseline() -> None:
    base = {s.series_id for s in load_spec(SPEC_PATHS["baseline"])}
    fisc = {s.series_id for s in load_spec(SPEC_PATHS["fiscal"])}
    assert len(fisc) == 35
    assert base < fisc
    assert fisc - base == {"GCEC1", "MTSDS133FMS", "W875RX1"}


def test_quarterly_series_identified() -> None:
    q = {s.series_id for s in load_spec(SPEC_PATHS["fiscal"]) if s.frequency == "q"}
    assert q == {"GDPC1", "ULCNFB", "A261RX1Q020SBEA", "GCEC1"}


def test_spec_fields_typed() -> None:
    sp = next(s for s in load_spec(SPEC_PATHS["fiscal"]) if s.series_id == "GDPC1")
    assert sp.frequency == "q"
    assert sp.transform == "pca"
    assert isinstance(sp.model, int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_spec.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gdpnowcast.data.spec'`

- [ ] **Step 3: Write `spec.py`**

```python
"""Load the FRBNY-style model spec (Spec_US_*.xlsx) into typed records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATHS = {
    "baseline": REPO_ROOT / "Spec_US_new.xlsx",
    "fiscal": REPO_ROOT / "Spec_US_fiscal.xlsx",
}


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    name: str
    frequency: str  # "m" or "q"
    transform: str  # lin / chg / ch1 / pch / pc1 / pca / log
    model: int
    category: str


def load_spec(path: Path) -> list[SeriesSpec]:
    df = pd.read_excel(path, sheet_name="spec")
    return [
        SeriesSpec(
            series_id=str(r["SeriesID"]).strip(),
            name=str(r["SeriesName"]).strip(),
            frequency=str(r["Frequency"]).strip().lower(),
            transform=str(r["Transformation"]).strip(),
            model=int(r["Model"]),
            category=str(r["Category"]).strip(),
        )
        for _, r in df.iterrows()
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_spec.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/data/spec.py tests/test_spec.py
git commit -m "feat(phase2): typed series-spec loader"
```

---

### Task 3: ALFRED point-in-time reconstruction (no network in tests)

**Files:**
- Create: `src/gdpnowcast/data/fred.py`
- Test: `tests/test_reconstruction.py`

- [ ] **Step 1: Write the failing test** (`tests/test_reconstruction.py`)

Tests use a hand-built synthetic release history — no network — so they are deterministic and run in CI.

```python
import pandas as pd

from gdpnowcast.data.fred import asof_series, reconstruct_asof


def _history() -> pd.DataFrame:
    # obs 2020-01-01 first published 2020-02-15 (=100), revised 2020-05-15 (=110)
    # obs 2020-02-01 first published 2020-03-15 (=200)
    return pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(
                ["2020-02-15", "2020-05-15", "2020-03-15"]
            ),
            "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01"]),
            "value": [100.0, 110.0, 200.0],
        }
    )


def test_asof_takes_latest_realtime_not_after_d() -> None:
    s = reconstruct_asof(_history(), pd.Timestamp("2020-04-01"))
    # the 2020-05-15 revision is in the future as of 2020-04-01 -> excluded
    assert s.loc[pd.Timestamp("2020-01-01")] == 100.0
    assert s.loc[pd.Timestamp("2020-02-01")] == 200.0


def test_asof_sees_revision_once_published() -> None:
    s = reconstruct_asof(_history(), pd.Timestamp("2020-06-01"))
    assert s.loc[pd.Timestamp("2020-01-01")] == 110.0


def test_asof_excludes_observations_after_d() -> None:
    # nothing observed after the vintage date can appear
    s = reconstruct_asof(_history(), pd.Timestamp("2020-01-20"))
    assert s.empty  # first publication (2020-02-15) is after 2020-01-20


def test_quarterly_shift_lands_on_last_month_of_quarter() -> None:
    hist = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2020-04-30"]),
            "date": pd.to_datetime(["2020-01-01"]),  # Q1, quarter-start stamp
            "value": [5.0],
        }
    )
    s = asof_series(hist, pd.Timestamp("2020-06-01").date(), frequency="q")
    assert pd.Timestamp("2020-03-01") in s.index  # Jan + 2 months = Mar
    assert pd.Timestamp("2020-01-01") not in s.index
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_reconstruction.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gdpnowcast.data.fred'`

- [ ] **Step 3: Write `fred.py`**

```python
"""ALFRED point-in-time fetch + local as-of reconstruction.

Forward-looking-bias guardrail (Matteo's standing concern, napkin Domain #4):
reconstruct_asof keeps, for each observation date, only the latest value whose
realtime_start <= D, and never returns an observation dated after D. No ffill,
no interpolation, no backfill — missing cells stay missing."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_START = pd.Timestamp("1985-01-01")


def get_fred() -> Fred:
    # override=True: .env is the single source of truth; a stale OS-level
    # FRED_API_KEY (e.g. Windows User env) must not shadow it. See napkin Tooling #3.
    load_dotenv(REPO_ROOT / ".env", override=True)
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Fred(api_key=key)


def fetch_release_history(fred: Fred, series_id: str) -> pd.DataFrame:
    """Full ALFRED release history: tidy [realtime_start, date, value] (float)."""
    raw = fred.get_series_all_releases(series_id)
    df = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(raw["realtime_start"]),
            "date": pd.to_datetime(raw["date"]),
            "value": pd.to_numeric(raw["value"], errors="coerce"),
        }
    )
    return df.dropna(subset=["value"]).reset_index(drop=True)


def reconstruct_asof(history: pd.DataFrame, as_of: pd.Timestamp) -> pd.Series:
    """Series as known at as_of: latest value per obs date with realtime_start <= as_of,
    restricted to observations dated <= as_of. Quarter-start stamping is preserved
    (no shift here — that is applied in asof_series)."""
    known = history[history["realtime_start"] <= as_of]
    if known.empty:
        return pd.Series(dtype=float)
    s = known.sort_values("realtime_start").groupby("date")["value"].last().sort_index()
    return s[s.index <= as_of]


def asof_series(history: pd.DataFrame, as_of: date, frequency: str) -> pd.Series:
    """reconstruct_asof + quarterly stamping. Quarterly series (frequency='q') are
    shifted +2 months so a quarter-start observation lands on the last month of the
    quarter (Mar/Jun/Sep/Dec), matching the v1 ingest convention (napkin Domain #1)."""
    s = reconstruct_asof(history, pd.Timestamp(as_of))
    if frequency == "q" and not s.empty:
        s = s.copy()
        s.index = s.index + pd.DateOffset(months=2)
    return s
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_reconstruction.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/data/fred.py tests/test_reconstruction.py
git commit -m "feat(phase2): ALFRED point-in-time reconstruction (no-leakage)"
```

---

### Task 4: No-leakage cross-validation against the live API (network, slow)

This is the guardrail that proves the reconstruction (D1) equals the authoritative point-in-time API and never leaks future data. It is marked `slow` and skips when no FRED key is available (so CI without the secret stays green).

**Files:**
- Test: `tests/test_fetch_integration.py`

- [ ] **Step 1: Write the cross-validation test** (`tests/test_fetch_integration.py`)

```python
import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

from gdpnowcast.data.fred import fetch_release_history, get_fred, reconstruct_asof

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=True)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("FRED_API_KEY"),
        reason="needs FRED_API_KEY (.env) — skipped in offline CI",
    ),
]


@pytest.mark.parametrize("series_id", ["PPIFIS", "GCEC1", "PAYEMS"])
@pytest.mark.parametrize("as_of", ["2018-07-06", "2020-04-01", "2023-01-03"])
def test_reconstruction_matches_direct_pointintime(series_id: str, as_of: str) -> None:
    fred = get_fred()
    history = fetch_release_history(fred, series_id)
    recon = reconstruct_asof(history, pd.Timestamp(as_of)).dropna()
    direct = fred.get_series(series_id, realtime_start=as_of, realtime_end=as_of).dropna()
    direct.index = pd.to_datetime(direct.index)
    # same observation coverage and identical values (point-in-time, no leakage)
    assert list(recon.index) == list(direct.index)
    pd.testing.assert_series_equal(
        recon, direct, check_names=False, check_freq=False, rtol=0, atol=0
    )


@pytest.mark.parametrize("as_of", ["2017-01-03", "2021-04-01"])
def test_no_observation_after_vintage(as_of: str) -> None:
    fred = get_fred()
    history = fetch_release_history(fred, "PAYEMS")
    recon = reconstruct_asof(history, pd.Timestamp(as_of))
    assert recon.index.max() <= pd.Timestamp(as_of)
```

- [ ] **Step 2: Run the slow test locally (with key)**

Run: `uv run pytest tests/test_fetch_integration.py -v -m slow`
Expected: PASS (11 tests: 9 parametrized cross-checks + 2 leakage checks). If a value mismatch appears, STOP — the reconstruction is leaking or mis-ordering; do not proceed to the full fetch.

- [ ] **Step 3: Confirm the offline lane excludes them**

Run: `uv run pytest -m "not slow" -v`
Expected: the integration tests are **deselected** (the fast lane, wired into `just test` + the GitHub workflow). Note: without an `-m` filter the slow tests still run locally when a key is present, and auto-**skip** in CI (no `.env`/secret) via `skipif`. The `slow` marker only *excludes* them when `-m "not slow"` is passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_fetch_integration.py
git commit -m "test(phase2): cross-validate reconstruction vs live point-in-time API"
```

---

### Task 5: Vintage file builder

**Files:**
- Create: `src/gdpnowcast/data/builder.py`
- Test: `tests/test_builder.py`

- [ ] **Step 1: Write the failing test** (`tests/test_builder.py`)

```python
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from gdpnowcast.data.builder import build_vintage, monthly_index, write_vintage
from gdpnowcast.data.spec import SeriesSpec


def _specs() -> list[SeriesSpec]:
    return [
        SeriesSpec("PAYEMS", "Payroll", "m", "chg", 1, "Labor"),
        SeriesSpec("GDPC1", "GDP", "q", "pca", 1, "National Accounts"),
    ]


def _histories() -> dict[str, pd.DataFrame]:
    payems = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2019-02-01", "2019-03-01"]),
            "date": pd.to_datetime(["2019-01-01", "2019-02-01"]),
            "value": [150000.0, 150500.0],
        }
    )
    gdp = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2019-01-30"]),
            "date": pd.to_datetime(["2018-10-01"]),  # Q4 2018, quarter-start stamp
            "value": [19000.0],
        }
    )
    return {"PAYEMS": payems, "GDPC1": gdp}


def test_monthly_index_runs_1985_to_vintage_month() -> None:
    idx = monthly_index(date(2020, 7, 25))
    assert idx[0] == pd.Timestamp("1985-01-01")
    assert idx[-1] == pd.Timestamp("2020-07-01")
    assert (idx.day == 1).all()


def test_build_vintage_format() -> None:
    df = build_vintage(_histories(), _specs(), date(2019, 3, 15))
    assert list(df.columns) == ["Date", "PAYEMS", "GDPC1"]
    assert df["Date"].iloc[0] == pd.Timestamp("1985-01-01")
    assert df["Date"].iloc[-1] == pd.Timestamp("2019-03-01")
    # monthly value present, future months NaN (no leakage / no ffill)
    row_jan = df.loc[df["Date"] == pd.Timestamp("2019-01-01"), "PAYEMS"].iloc[0]
    assert row_jan == 150000.0
    assert np.isnan(df.loc[df["Date"] == pd.Timestamp("2019-03-01"), "PAYEMS"].iloc[0])
    # quarterly GDP stamped on Dec (Q4 last month), not Oct
    assert df.loc[df["Date"] == pd.Timestamp("2018-12-01"), "GDPC1"].iloc[0] == 19000.0
    assert np.isnan(df.loc[df["Date"] == pd.Timestamp("2018-10-01"), "GDPC1"].iloc[0])


def test_write_vintage_roundtrip(tmp_path: Path) -> None:
    df = build_vintage(_histories(), _specs(), date(2019, 3, 15))
    path = write_vintage(df, tmp_path, date(2019, 3, 15))
    assert path.name == "2019-03-15.xlsx"
    back = pd.read_excel(path)
    assert "Date" in back.columns
    assert {"PAYEMS", "GDPC1"} <= set(back.columns)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gdpnowcast.data.builder'`

- [ ] **Step 3: Write `builder.py`**

```python
"""Assemble a point-in-time vintage into the v1 Excel format:
a monthly `Date` column (1985-01 .. vintage month) + one column per SeriesID,
quarterly series stamped on the last month of the quarter, missing cells NaN."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .fred import DATA_START, asof_series
from .spec import SeriesSpec


def monthly_index(as_of: date) -> pd.DatetimeIndex:
    end = pd.Timestamp(as_of.year, as_of.month, 1)
    return pd.date_range(DATA_START, end, freq="MS")


def build_vintage(
    histories: dict[str, pd.DataFrame], specs: list[SeriesSpec], as_of: date
) -> pd.DataFrame:
    idx = monthly_index(as_of)
    df = pd.DataFrame(index=idx)
    for sp in specs:
        series = asof_series(histories[sp.series_id], as_of, sp.frequency)
        df[sp.series_id] = series.reindex(idx)  # reindex -> NaN for missing, never ffill
    df.index.name = "Date"
    return df.reset_index()


def write_vintage(df: pd.DataFrame, out_dir: Path, as_of: date) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{as_of.isoformat()}.xlsx"
    df.to_excel(path, index=False)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_builder.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdpnowcast/data/builder.py tests/test_builder.py
git commit -m "feat(phase2): vintage Excel builder matching v1 load_data format"
```

---

### Task 6: CLI `fetch` command + justfile wiring

**Files:**
- Create: `src/gdpnowcast/cli.py`
- Modify: `justfile:32-35`
- Test: `tests/test_fetch_integration.py` (extend with a 2-vintage smoke)

- [ ] **Step 1: Write `cli.py`**

```python
"""Unified Typer CLI. Phase 2 wires `fetch`; later phases add estimate/run/etc."""

from __future__ import annotations

from pathlib import Path

import typer

from .data.builder import build_vintage, write_vintage
from .data.fred import fetch_release_history, get_fred
from .data.spec import SPEC_PATHS, load_spec
from .data.vintages import load_manifest

app = typer.Typer(add_completion=False, help="GDPnowcast-fiscal CLI")

_OUT_SUBDIR = {"baseline": "US_new", "fiscal": "US_fiscal"}
_DATA_ROOT = Path("data")


@app.callback()
def _main() -> None:
    """GDPnowcast-fiscal CLI. Keeps the multi-command structure (estimate/run come later)."""
    # Without a callback, Typer collapses a single-command app and `gdpnowcast fetch`
    # would treat "fetch" as an arg. The callback forces the `gdpnowcast <command>` form.


@app.command()
def fetch(
    variant: str = typer.Option("fiscal", help="baseline (32 series) | fiscal (35)"),
    data_dir: Path = typer.Option(_DATA_ROOT, help="output root (gitignored)"),
    limit: int = typer.Option(0, help="only the first N vintages (0 = all; for smoke)"),
) -> None:
    """Rebuild ALFRED point-in-time vintage Excel files for a variant."""
    if variant not in SPEC_PATHS:
        raise typer.BadParameter(f"variant must be one of {sorted(SPEC_PATHS)}")
    specs = load_spec(SPEC_PATHS[variant])
    vintages = load_manifest(variant)
    if limit:
        vintages = vintages[:limit]
    out_dir = data_dir / _OUT_SUBDIR[variant]

    fred = get_fred()
    typer.echo(f"fetching {len(specs)} release histories from ALFRED ...")
    histories = {sp.series_id: fetch_release_history(fred, sp.series_id) for sp in specs}

    written = 0
    for v in vintages:
        if (out_dir / f"{v.isoformat()}.xlsx").exists():
            continue  # resumable checkpoint
        write_vintage(build_vintage(histories, specs, v), out_dir, v)
        written += 1
    typer.echo(f"done: {variant} -> {out_dir} ({written} new, {len(vintages)} total)")


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Replace the justfile placeholder** (`justfile:32-35`)

```just
# Phase 2 — rebuild ALFRED vintage files. `just fetch fiscal` or `just fetch baseline`.
fetch variant="fiscal":
    uv run gdpnowcast fetch --variant {{variant}}
```

**Slow-lane plumbing (added during execution so network tests don't pollute the default CI lane):**
- `justfile`: change `test` to `uv run pytest -m "not slow" ...` and add a `test-slow:` recipe (`uv run pytest -m slow -v`).
- `.github/workflows/test.yml`: change the pytest step to `uv run pytest -m "not slow" ...`.
- `pyproject.toml`: add `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls = ["typer.Option", "typer.Argument"]` so B008 doesn't flag Typer's DI defaults.

- [ ] **Step 3: Verify the CLI is wired**

Run: `uv run gdpnowcast --help` then `uv run gdpnowcast fetch --help`
Expected: help text lists the `fetch` command with `--variant`, `--data-dir`, `--limit`.

- [ ] **Step 4: Add a 2-vintage smoke test** (append to `tests/test_fetch_integration.py`)

```python
def test_fetch_smoke_two_vintages(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from gdpnowcast.cli import app

    result = CliRunner().invoke(
        app,
        ["fetch", "--variant", "fiscal", "--data-dir", str(tmp_path), "--limit", "2"],
    )
    assert result.exit_code == 0, result.output
    out = sorted((tmp_path / "US_fiscal").glob("*.xlsx"))
    assert len(out) == 2
    back = pd.read_excel(out[0])
    assert "Date" in back.columns
    assert len([c for c in back.columns if c != "Date"]) == 35
```

- [ ] **Step 5: Run the smoke test (needs key; slow)**

Run: `uv run pytest tests/test_fetch_integration.py::test_fetch_smoke_two_vintages -v -m slow`
Expected: PASS — writes the 2 earliest fiscal vintages (`2016-10-03.xlsx`, `2016-12-07.xlsx`) into a temp dir, 35 series columns.

- [ ] **Step 6: Commit**

```bash
git add src/gdpnowcast/cli.py justfile tests/test_fetch_integration.py
git commit -m "feat(phase2): gdpnowcast fetch CLI + justfile wiring"
```

---

### Task 7: Superset assertion + value-reproduction diagnostic

The hard Phase 2 exit gate (design-doc §7). Runs after a full fetch (Task 9) but the test is written now and skips if the data isn't built yet.

**Files:**
- Create: `tests/test_superset.py`
- Create: `tools/compare_to_v1.py` (diagnostic, dev tool)

- [ ] **Step 1: Write the superset test** (`tests/test_superset.py`)

```python
from datetime import date
from pathlib import Path

import pytest

from gdpnowcast.data.vintages import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
_DIRS = {"baseline": "US_new", "fiscal": "US_fiscal"}


def _built(variant: str) -> set[date]:
    d = REPO_ROOT / "data" / _DIRS[variant]
    return {date.fromisoformat(f.stem) for f in d.glob("*.xlsx")} if d.exists() else set()


@pytest.mark.parametrize("variant", ["baseline", "fiscal"])
def test_generated_is_superset_of_manifest(variant: str) -> None:
    # Gate on the v1 backup dir: it is created by Task 9 Step 1 right before the
    # full fetch, so its presence means data/<dir>/ now holds OUR generated files
    # (not the v1 files still on disk pre-fetch). Skip until then.
    backup = REPO_ROOT / "data" / f"{_DIRS[variant]}_v1"
    if not backup.exists():
        pytest.skip(f"{variant}: full fetch not run yet (no _v1 backup; see Task 9)")
    built = _built(variant)
    manifest = set(load_manifest(variant))
    missing = sorted(manifest - built)
    assert not missing, f"{variant}: {len(missing)} manifest vintages not generated: {missing[:10]}"
```

> **Why the backup gate (learned during execution):** v1's vintage files are already on disk in `data/US_new/` (486) and `data/US_fiscal/` (485). A naive "skip if empty" never skips, and the fiscal check would fail on the D2 gap (2021-01-04) by comparing against the *old* v1 files. Gating on the `_v1` backup makes the test meaningful only after Task 9 has moved v1 aside and regenerated into a clean dir.

- [ ] **Step 2: Write the diagnostic** (`tools/compare_to_v1.py`)

```python
"""Diagnostic (NOT a gate): compare newly-fetched vintage values to the v1 files
on disk for a sample of vintages. The 3 fiscal series were ALFRED-sourced in v1
and should match closely; the 32 baseline came from a different v1 source and may
diverge — report deltas honestly for docs/data_sources.md (see Decision D3)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(variant: str = "fiscal") -> None:
    subdir = {"baseline": "US_new", "fiscal": "US_fiscal"}[variant]
    v1_dir = REPO_ROOT / "data" / subdir
    sample = sorted(v1_dir.glob("*.xlsx"))[:: max(1, len(list(v1_dir.glob("*.xlsx"))) // 10)]
    for f in sample:
        v1 = pd.read_excel(f).set_index("Date")
        # NOTE: requires a parallel freshly-fetched copy; here we assume in-place
        # rebuild was diffed before overwrite, or compare against a backup dir.
        print(f"{f.name}: {v1.shape[1]} series, "
              f"non-null cells={int(v1.notna().to_numpy().sum())}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fiscal")
```

(The diagnostic's exact diff mechanics are finalized in Task 9 once a backup of the v1 files is taken before overwrite — see Task 9 Step 1.)

- [ ] **Step 3: Run the superset test (skips pre-fetch)**

Run: `uv run pytest tests/test_superset.py -v`
Expected: 2 SKIPPED (no `_v1` backup yet → the gated fetch hasn't run). After Task 9 (which creates the backup + regenerates) it must PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_superset.py tools/compare_to_v1.py
git commit -m "test(phase2): vintage superset assertion + v1 value diagnostic"
```

---

### Task 8: `docs/data_sources.md`

**Files:**
- Create: `docs/data_sources.md`

- [ ] **Step 1: Write the data-sources doc**

Document, with a table generated from `Spec_US_fiscal.xlsx`: every `SeriesID`, `SeriesName`, `Frequency`, `Transformation`, `Model` flag, `Category`. Then prose sections:
- **Vintage strategy:** manifest-driven (485 fiscal / 486 baseline real v1 dates), includes the 33 quarter-start re-estimation vintages, range 2016-10-03 .. 2025-07-25.
- **Point-in-time / no-leakage policy** (verbatim guardrail): `realtime_start=realtime_end=D` semantics via `reconstruct_asof`; never ffill/interpolate/backfill; observations truncated to `<= D`; cross-validated against the live API (Task 4).
- **Coverage spike result:** GO 35/35, per-series earliest vintage table (from `tools/alfred_coverage_spike.py` output), tightest = MTSDS133FMS 2015-09-11.
- **Quarterly convention:** `+2`-month shift to last-month-of-quarter (napkin Domain #1), affects GDPC1/ULCNFB/A261RX1Q020SBEA/GCEC1.
- **Known v1 quirks:** the `2021-01-04` fiscal-set gap (Decision D2); baseline-series provenance divergence (Decision D3); the burned-then-rotated FRED key.

- [ ] **Step 2: Self-review the doc end-to-end** (napkin User-Directive #4)

Re-read the full doc for internal consistency (series count, vintage count, dates, cross-refs). Report findings.

- [ ] **Step 3: Commit**

```bash
git add docs/data_sources.md
git commit -m "docs(phase2): data sources, vintage strategy, no-leakage policy"
```

---

### Task 9: Full fetch run + Phase 2 exit verification (GATED)

**Pre-req gate (human):** before the full write of ~970 Excel files, exclude `data/` (and `.venv`) from OneDrive sync to avoid sync churn/locks (napkin Tooling #1). Confirm with Matteo.

**Files:**
- Writes (gitignored): `data/US_new/*.xlsx` (486), `data/US_fiscal/*.xlsx` (485).
- Modify: `RESUME.md`.

- [ ] **Step 1: Back up the v1 files for the diagnostic**

```bash
# preserve v1's vintage files so the new fetch can be diffed (D3 diagnostic)
mv data/US_fiscal data/US_fiscal_v1 ; mv data/US_new data/US_new_v1
```
(These backups stay gitignored; they let `tools/compare_to_v1.py` diff new vs v1 before we trust the rebuild.)

- [ ] **Step 2: Run the full fetch for both variants**

Run:
```
uv run gdpnowcast fetch --variant baseline
uv run gdpnowcast fetch --variant fiscal
```
Expected: each prints `fetching 32/35 release histories ...` then `done: ... (486 new, 486 total)` for both variants (486 each after D2). ~67 API calls total (32 + 35 histories, re-fetched per variant; acceptable). Wall time dominated by writing ~972 xlsx files, not the network.

- [ ] **Step 3: Run the superset assertion**

Run: `uv run pytest tests/test_superset.py -v`
Expected: PASS (2 tests) — generated ⊇ manifest for both variants.

- [ ] **Step 4: Run the value diagnostic vs v1 backups**

Finalize `tools/compare_to_v1.py` to diff `data/US_fiscal/<d>.xlsx` against `data/US_fiscal_v1/<d>.xlsx` for ~10 sampled vintages (skip dates with no v1 counterpart, e.g. the added `2021-01-04` in fiscal); report per-series max abs/rel delta. Expected: the 3 fiscal series match within float tolerance; baseline deltas (if any) are recorded in `data_sources.md` (D3). Do NOT gate on baseline equality.

Run: `uv run python tools/compare_to_v1.py fiscal`

- [ ] **Step 5: Full CI**

Run: `just ci`  (lint + typecheck + test; slow/network tests skip without `-m slow`)
Expected: green. Then optionally `uv run pytest -m slow` locally (with key) for the full network suite.

- [ ] **Step 6: Update RESUME + commit (code/docs only — never `data/`)**

```bash
git add RESUME.md
git commit -m "docs(phase2): mark Phase 2 data pipeline complete (superset GO)"
```
Confirm `git status` shows NO `data/` files staged (they are gitignored).

---

## Self-Review (against the design doc + backlog)

**1. Spec coverage:**
- Design-doc §3 Phase 2 "build a NEW 32-series fetcher, not a port" → Tasks 2-6 build net-new `data/*.py`; Decision-D-section + Context state it explicitly. ✔
- §3/§7 "vintage list includes the 33 quarter-start vintages, not Fridays-only" → Task 1 manifest + `test_manifest_includes_all_quarter_starts`. ✔
- §7 Phase 2 exit "superset assertion (≥485, all present), not a 5-sample" → Task 7 `test_generated_is_superset_of_manifest` + Task 9. ✔
- §8 open-q #2 ALFRED coverage spike → done pre-plan (GO 35/35), recorded in Context + Task 8. ✔
- §8 risk "never interpolate/backfill an as-of cell (leaks future data)" + Matteo's forward-looking-bias directive → `reconstruct_asof` (no ffill), Task 3 unit tests, Task 4 live cross-validation, Task 5 NaN-not-ffill test. ✔
- §4 `realtime_start=realtime_end` point-in-time semantics → `reconstruct_asof` + Task 4 proves equality with the direct API. ✔
- `load_dotenv(override=True)` gotcha → `get_fred()` in Task 3. ✔
- 4 quarterly series + last-month-of-quarter convention → Task 2 `test_quarterly_series_identified`, Task 3 shift test, Task 5 builder test. ✔
- pyproject `gdpnowcast.cli:app` had no module → Task 6 creates `cli.py`. ✔

**2. Placeholder scan:** No "TBD/TODO/handle errors". The one soft spot — `tools/compare_to_v1.py` diff mechanics — is explicitly finalized in Task 9 Step 4 (needs the v1 backup created in Task 9 Step 1), and it is a diagnostic, not a gate. Acceptable and flagged.

**3. Type consistency:** `SeriesSpec(series_id, name, frequency, transform, model, category)` is used identically in Tasks 2/5/6. `asof_series(history, as_of: date, frequency)` and `reconstruct_asof(history, as_of: pd.Timestamp)` signatures are consistent across Tasks 3/5. `load_manifest(variant)`/`load_spec(path)`/`SPEC_PATHS` consistent across Tasks 1/2/6. `build_vintage(histories, specs, as_of)` / `write_vintage(df, out_dir, as_of)` consistent across Tasks 5/6. ✔

**4. Open risk to watch during execution:** if Task 4 reveals any value mismatch (reconstruction ≠ direct API), STOP and fall back to Decision-D1's per-vintage approach before Task 9. If baseline values diverge materially from v1 (D3), that is expected and documented, not a failure.

---

## Execution Handoff

Two execution options:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks, fast iteration. Uses `superpowers:subagent-driven-development`.
2. **Inline Execution** — execute tasks in this session with checkpoints. Uses `superpowers:executing-plans`.

Given Matteo's incremental-orchestration preference, **inline execution with a review checkpoint after each task** fits best. Confirm Decisions D1/D2/D3 (Task 0) before starting Task 1.
