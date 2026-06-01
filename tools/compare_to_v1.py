"""Diagnostic (NOT a gate): compare newly-fetched vintage values to the v1 backup
(data/US_*_v1/). Reports THREE things, because "values match where both are
populated" is necessary but NOT sufficient:

  1. both-populated: max abs delta per series (are shared cells equal?)
  2. v2-has / v1-NaN: cells we filled that v1 left empty (e.g. longer history)
  3. v1-has / v2-NaN: cells v1 filled that we left empty (misalignment / gaps)

(2) and (3) are the asymmetric directions an earlier both-non-NaN-only check
missed; they revealed v1's longer-vs-shorter series starts and a v1 quarterly
stamping quirk in ~10 year-end vintages. See docs/data_sources.md.

Run after the fetch (data/US_*_v1 must exist).
Usage:  uv run python tools/compare_to_v1.py [baseline|fiscal] [n_sample]
        n_sample = 0 (default) scans ALL vintages; >0 takes an even sample.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
_SUBDIR = {"baseline": "US_new", "fiscal": "US_fiscal"}


def _load(path: Path) -> pd.DataFrame:
    return pd.read_excel(path).set_index("Date")


def main(variant: str = "fiscal", n: int = 0) -> None:
    new_dir = REPO_ROOT / "data" / _SUBDIR[variant]
    v1_dir = REPO_ROOT / "data" / f"{_SUBDIR[variant]}_v1"
    if not v1_dir.exists():
        print(f"no v1 backup at {v1_dir} - run the fetch (Task 9) first")
        return
    files = sorted(new_dir.glob("*.xlsx"))
    if not files:
        print(f"no fetched files in {new_dir} - run `just fetch {variant}` first")
        return
    if n > 0:
        files = files[:: max(1, len(files) // n)]

    worst: dict[str, float] = {}
    v2_only: Counter = Counter()  # v2 has a value, v1 NaN (same date+series)
    v1_only: Counter = Counter()  # v1 has a value, v2 NaN
    v1_only_vintages: list[tuple[str, int]] = []
    compared = 0
    no_v1 = 0
    for f in files:
        v1file = v1_dir / f.name
        if not v1file.exists():
            no_v1 += 1
            continue
        new, old = _load(f), _load(v1file)
        common = [c for c in new.columns if c in old.columns]
        a, b = new[common].align(old[common], join="inner", axis=0)  # same dates
        a_na, b_na = a.isna(), b.isna()
        c1_here = 0
        for c in common:
            both = (~a_na[c]) & (~b_na[c])
            if both.any():
                diff = (a[c][both] - b[c][both]).abs().to_numpy()
                worst[c] = max(worst.get(c, 0.0), float(np.nanmax(diff)))
            v2_only[c] += int(((~a_na[c]) & b_na[c]).sum())
            k1 = int((a_na[c] & (~b_na[c])).sum())
            v1_only[c] += k1
            c1_here += k1
        if c1_here:
            v1_only_vintages.append((f.name, c1_here))
        compared += 1

    scope = f"ALL {compared}" if n <= 0 else f"{compared} sampled"
    print(f"== {variant}: {scope} vintages compared ({no_v1} had no v1 counterpart) ==")
    print("\n[1] max abs delta where BOTH populated (shared cells):")
    for c, m in sorted(worst.items(), key=lambda kv: -kv[1]):
        print(f"    {c:20s} {m:.6g}{'  <-- diverges' if m > 1e-6 else ''}")
    nz2 = {c: k for c, k in v2_only.items() if k}
    nz1 = {c: k for c, k in v1_only.items() if k}
    print(f"\n[2] cells v2-has / v1-NaN  (total {sum(nz2.values())}): {nz2 or 'none'}")
    print(f"\n[3] cells v1-has / v2-NaN  (total {sum(nz1.values())}): {nz1 or 'none'}")
    if v1_only_vintages:
        print(
            f"    vintages with v1-only cells ({len(v1_only_vintages)}): "
            f"{[v for v, _ in v1_only_vintages[:15]]}"
        )


if __name__ == "__main__":
    variant = sys.argv[1] if len(sys.argv) > 1 else "fiscal"
    n_sample = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    main(variant, n_sample)
