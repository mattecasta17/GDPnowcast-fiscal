"""Verify the configs/quarters.json registry against the on-disk vintage panels.

Reports, per variant (US_new baseline, US_fiscal fiscal), which weekly vintages and
prev/curr param vintages are MISSING on disk -- so the Phase-4 backtest's coverage gaps
are explicit (honest research) rather than silently skipped at run time. Also re-asserts
the back-compat invariant that CONFIG_2017Q1 is unchanged by the JSON-loader refactor.

Usage (from repo root):
    uv run python -m tools.check_quarter_data
"""

from __future__ import annotations

from pathlib import Path

from gdpnowcast.nowcast.config import CONFIG_2017Q1, CONFIGS

REPO = Path(__file__).resolve().parents[1]
VARIANTS = {"baseline": "US_new", "fiscal": "US_fiscal"}


def _check_invariants() -> None:
    assert len(CONFIGS) == 34, f"expected 34 quarters, got {len(CONFIGS)}"
    c = CONFIG_2017Q1
    assert c.advance_date == "2017-04-28", c.advance_date
    assert c.prev_vintage == "2016-10-03" and c.curr_vintage == "2017-01-03"
    assert c.switch_date == "2017-01-01" and c.gdp_actual == 0.7
    assert len(c.vintages) == 22 and c.vintages[-1] == "2017-04-28"
    print(f"invariants OK: {len(CONFIGS)} quarters, CONFIG_2017Q1 unchanged\n")


def main() -> None:
    _check_invariants()
    for variant, subdir in VARIANTS.items():
        d = REPO / "data" / subdir
        missing_weekly: dict[str, list[str]] = {}
        missing_param: dict[str, list[str]] = {}
        for period, cfg in CONFIGS.items():
            for v in cfg.vintages:
                if not (d / f"{v}.xlsx").exists():
                    missing_weekly.setdefault(period, []).append(v)
            for v in (cfg.prev_vintage, cfg.curr_vintage):
                if not (d / f"{v}.xlsx").exists():
                    missing_param.setdefault(period, []).append(v)
        total_w = sum(len(x) for x in missing_weekly.values())
        total_p = sum(len(x) for x in missing_param.values())
        present = "PRESENT" if d.exists() else "MISSING DIR"
        print(f"== {variant} ({subdir}, {present}) ==  missing weekly={total_w} param={total_p}")
        for period in sorted(set(missing_weekly) | set(missing_param)):
            print(
                f"  {period}: weekly={missing_weekly.get(period, [])} "
                f"param={missing_param.get(period, [])}"
            )
        print()


if __name__ == "__main__":
    main()
