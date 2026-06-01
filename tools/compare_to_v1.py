"""Diagnostic (NOT a gate): compare newly-fetched vintage values to the v1 backup
(data/US_*_v1/) for a sample of vintages. The 3 fiscal series were ALFRED-sourced
in v1 and should match closely; the 32 baseline came from a different v1 source and
may diverge - report deltas honestly for docs/data_sources.md (Decision D3).

Run after Task 9 Step 1 (which renames the v1 dirs to data/US_*_v1) and the fetch.
Usage:  uv run python tools/compare_to_v1.py [baseline|fiscal] [n_sample]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
_SUBDIR = {"baseline": "US_new", "fiscal": "US_fiscal"}


def _load(path: Path) -> pd.DataFrame:
    return pd.read_excel(path).set_index("Date")


def main(variant: str = "fiscal", n: int = 10) -> None:
    new_dir = REPO_ROOT / "data" / _SUBDIR[variant]
    v1_dir = REPO_ROOT / "data" / f"{_SUBDIR[variant]}_v1"
    if not v1_dir.exists():
        print(f"no v1 backup at {v1_dir} - run Task 9 Step 1 (rename v1 dirs) first")
        return
    files = sorted(new_dir.glob("*.xlsx"))
    if not files:
        print(f"no fetched files in {new_dir} - run `just fetch {variant}` first")
        return
    sample = files[:: max(1, len(files) // n)]
    worst: dict[str, float] = {}
    compared = 0
    for f in sample:
        v1file = v1_dir / f.name
        if not v1file.exists():
            print(f"{f.name}: no v1 counterpart (skip)")
            continue
        new, old = _load(f), _load(v1file)
        common = [c for c in new.columns if c in old.columns]
        a, b = new[common].align(old[common], join="inner", axis=0)
        for c in common:
            diff = (a[c] - b[c]).abs()
            m = float(np.nanmax(diff.to_numpy())) if diff.notna().any() else 0.0
            worst[c] = max(worst.get(c, 0.0), m)
        compared += 1
    print(f"== {variant}: max abs delta per series across {compared} sampled vintages ==")
    for c, m in sorted(worst.items(), key=lambda kv: -kv[1]):
        flag = "  <-- diverges" if m > 1e-6 else ""
        print(f"  {c:20s} {m:.6g}{flag}")


if __name__ == "__main__":
    variant = sys.argv[1] if len(sys.argv) > 1 else "fiscal"
    n_sample = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    main(variant, n_sample)
