"""Surgically refresh the weekly nowcast path of specific quarter(s) in the committed artifacts.

The SAFE counterpart to ``run_backtest.py`` for an incremental calendar edit: when a quarter's
``vintages`` list in ``configs/quarters.json`` changes (e.g. completing the 2025q1 weekly
calendar by adding four Fridays), only that quarter's *weekly path* moves. The off-grid
``(advance-1)`` HEADLINE nowcast -- and therefore every metric, Diebold-Mariano test and the
benchmark table -- is computed from a standalone vintage and is UNCHANGED.

So instead of re-running all 34 quarters (and risking an accidental full-JSON overwrite, since
``run_backtest._write_artifacts`` rewrites the file from only the quarters it ran), this tool:

  1. recomputes ONLY the requested period(s) for both variants (workers=1, in-process);
  2. ASSERTS the recomputed headline / gdp_actual / advance_date are byte-identical to the
     committed artifact -- a correctness + look-ahead-safety check: adding weekly cutoffs must
     NOT move the pre-advance headline. If it does, something leaked -> abort, change nothing;
  3. splices only ``weekly[period]`` and ``skipped[period]`` into the committed
     ``docs/dashboard_data/{baseline,fiscal}.json``, leaving all other quarters byte-identical.

Run ``tools.build_dashboard_data`` afterwards to refresh the consolidated dashboard bundle.

Usage (from repo root):
  uv run python -m tools.refresh_period_weekly                 # default: 2025q1
  uv run python -m tools.refresh_period_weekly --periods 2025q1,2025q2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gdpnowcast.nowcast.backtest import run_backtest

REPO = Path(__file__).resolve().parents[1]
DASHBOARD_DATA = REPO / "docs" / "dashboard_data"
VARIANT_CFG = {
    "baseline": ("US_new", "Spec_US_new.xlsx"),
    "fiscal": ("US_fiscal", "Spec_US_fiscal.xlsx"),
}
TOL = 1e-9


def _refresh_variant(variant: str, periods: list[str]) -> None:
    subdir, spec = VARIANT_CFG[variant]
    path = DASHBOARD_DATA / f"{variant}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    head_by_period = {r["period"]: r for r in data["headline"]}

    results = run_backtest(subdir, spec, periods=periods, workers=1)
    for r in results:
        period = r["period"]
        h = r["headline"]
        if h is None:
            raise SystemExit(f"{variant}/{period}: headline=None -- run build_headline_vintages")
        old = head_by_period[period]
        # The off-grid (advance-1) headline must NOT move when the weekly grid changes.
        dy = abs(float(h["y_new"]) - float(old["headline_nowcast"]))
        de = abs(float(h["error"]) - float(old["error"]))
        if dy > TOL or de > TOL:
            raise SystemExit(
                f"{variant}/{period}: headline MOVED (dy={dy:.2e}, de={de:.2e}) -- "
                "a weekly-grid edit must not change the pre-advance nowcast; aborting."
            )
        if (
            float(r["gdp_actual"]) != float(old["gdp_advance"])
            or r["advance_date"] != old["advance_date"]
        ):
            raise SystemExit(f"{variant}/{period}: gdp_actual/advance_date changed -- aborting.")

        n_old = len(data["weekly"][period])
        data["weekly"][period] = r["weekly"]
        data["skipped"][period] = r["skipped"]
        print(
            f"  {variant}/{period}: weekly {n_old} -> {len(r['weekly'])} rows, "
            f"skipped={r['skipped']} (headline unchanged at {old['headline_nowcast']:.6f})"
        )

    path.write_text(json.dumps(data, indent=2, default=float) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--periods", default="2025q1", help="comma-separated, e.g. 2025q1,2025q2")
    args = ap.parse_args()
    periods = [p for p in args.periods.split(",") if p]
    print(f"refreshing weekly path for {periods} (both variants, headline pinned) ...")
    for variant in ("baseline", "fiscal"):
        _refresh_variant(variant, periods)
    print("done -- now run: uv run python -m tools.build_dashboard_data")


if __name__ == "__main__":
    main()
