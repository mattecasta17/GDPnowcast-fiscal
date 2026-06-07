"""Build the (advance-1) pre-advance headline vintages for the Phase-4 backtest.

For each quarter in the registry (configs/quarters.json) and each variant, build the as-of
``(advance_date - 1 day)`` vintage -- the tightest cutoff that provably excludes the BEA GDP
advance AND its same-day co-releases (the release-day leak documented in
``docs/plans/2026-06-04-phase4.0-release-day-cutoff-decision.md``). Each file lands in
``data/<subdir>/<advance-1>.xlsx`` alongside the weekly Friday manifest -- same builder, same
fuller v2 panels (gate item-3 decision), gitignored.

``advance_date(Q)`` is recomputed from ALFRED (first ``realtime_start`` of Q's quarter-start
GDP observation) and ASSERTED against ``QuarterCfg.advance_date`` for ALL 34 quarters -- an
auditable guard against a stale date.

One ALFRED session: fetch the fiscal-spec (superset) release histories once, then build both
panels -- US_new with the baseline specs, US_fiscal with the fiscal specs. ``build_vintage`` is
spec-driven (it reads ``histories[sp.series_id]`` only for ``sp in specs``), so the baseline
file ignores the 3 extra fiscal series and is identical to a baseline-only fetch.

Uses the DATA spec (``load_spec`` -> ``list[SeriesSpec]``, what ``build_vintage`` consumes),
NOT the DFM ``load_dfm_spec``. Dev tool, NOT wired into the CLI. Needs FRED_API_KEY in .env
(``get_fred`` -> ``load_dotenv(override=True)``; napkin Tooling #3). ALFRED is hit only here;
the backtest reads the files offline.

Usage (from repo root):
    uv run python -m tools.build_headline_vintages
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from gdpnowcast.data.builder import build_vintage, write_vintage
from gdpnowcast.data.fred import fetch_release_history, get_fred
from gdpnowcast.data.spec import SPEC_PATHS, load_spec
from gdpnowcast.nowcast.config import CONFIGS, QuarterCfg

REPO = Path(__file__).resolve().parents[1]
VARIANTS = {"baseline": "US_new", "fiscal": "US_fiscal"}  # variant -> data subdir
TARGET = "GDPC1"


def _quarter_start(period: str) -> pd.Timestamp:
    """FRED-native quarter-start obs date for a 'YYYYqQ' period (2017q1 -> 2017-01-01)."""
    y_str, q_str = period.split("q")
    return pd.Timestamp(int(y_str), 3 * (int(q_str) - 1) + 1, 1)


def _advance_minus_1(cfg: QuarterCfg) -> date:
    return (pd.Timestamp(cfg.advance_date) - pd.Timedelta(days=1)).date()


def build() -> None:
    fred = get_fred()
    fiscal_specs = load_spec(SPEC_PATHS["fiscal"])  # superset of baseline
    print(f"fetching {len(fiscal_specs)} release histories from ALFRED ...")
    histories = {sp.series_id: fetch_release_history(fred, sp.series_id) for sp in fiscal_specs}
    gdp = histories[TARGET]

    # Auditable guard: every quarter's hand-stored advance_date must equal ALFRED's first
    # realtime_start of that quarter's GDP observation (covers all 34, not just 2017Q1).
    for cfg in CONFIGS.values():
        obs = _quarter_start(cfg.period)
        computed = gdp.loc[gdp["date"] == obs, "realtime_start"].min()
        if pd.isna(computed):
            raise SystemExit(f"{cfg.period}: no GDP observation dated {obs.date()} in ALFRED")
        computed = pd.Timestamp(computed).normalize()
        if computed != pd.Timestamp(cfg.advance_date):
            raise SystemExit(
                f"{cfg.period}: ALFRED advance {computed.date()} != cfg.advance_date "
                f"{cfg.advance_date} -- regenerate configs/quarters.json"
            )
    print(f"advance-date assert OK for all {len(CONFIGS)} quarters")

    built = skipped = 0
    for variant, subdir in VARIANTS.items():
        specs = load_spec(SPEC_PATHS[variant])
        out_dir = REPO / "data" / subdir
        for cfg in CONFIGS.values():
            as_of = _advance_minus_1(cfg)
            if (out_dir / f"{as_of.isoformat()}.xlsx").exists():
                skipped += 1
                continue
            write_vintage(build_vintage(histories, specs, as_of), out_dir, as_of)
            built += 1
    print(
        f"done: built {built}, skipped {skipped} existing ({len(VARIANTS)} variants x {len(CONFIGS)} quarters)"
    )


if __name__ == "__main__":
    build()
