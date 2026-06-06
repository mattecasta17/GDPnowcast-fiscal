"""Build the (advance-1) pre-advance headline vintages for the Phase-4 backtest.

For each wired quarter, build the as-of ``(advance_date - 1 day)`` vintage -- the
tightest cutoff that provably excludes the BEA GDP advance AND its same-day
co-releases (the release-day leak documented in
``docs/plans/2026-06-04-phase4.0-release-day-cutoff-decision.md``). The file lands
in ``data/US_new/<advance-1>.xlsx`` alongside the weekly Friday manifest -- same
builder, same fuller v2 panel (gate item-3 decision), gitignored.

``advance_date(Q)`` is recomputed from ALFRED (first ``realtime_start`` of Q's GDP
observation) and ASSERTED against the hand-entered ``QuarterCfg.advance_date`` --
an auditable guard against a stale date. ALFRED is hit only at build time; the
backtest reads the file offline.

Uses the DATA spec (``load_spec`` -> ``list[SeriesSpec]``, what ``build_vintage``
consumes), NOT the DFM ``load_dfm_spec`` -> ``DfmSpec``.

Dev tool, NOT wired into the CLI. Needs a working ``FRED_API_KEY`` in ``.env``
(``get_fred`` -> ``load_dotenv(override=True)``; napkin Tooling #3).

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
from gdpnowcast.nowcast.config import CONFIG_2017Q1, QuarterCfg

REPO = Path(__file__).resolve().parents[1]
OUT_SUBDIR = "US_new"  # the fuller v2 baseline panel (gate item-3 decision)
TARGET = "GDPC1"

# Only 2017Q1 is wired for the first Phase-4-body step; add quarters here later.
CONFIGS: tuple[QuarterCfg, ...] = (CONFIG_2017Q1,)


def _quarter_start(period: str) -> pd.Timestamp:
    """FRED-native quarter-start obs date for a 'YYYYqQ' period (2017q1 -> 2017-01-01)."""
    y_str, q_str = period.split("q")
    return pd.Timestamp(int(y_str), 3 * (int(q_str) - 1) + 1, 1)


def _advance_minus_1(cfg: QuarterCfg) -> date:
    return (pd.Timestamp(cfg.advance_date) - pd.Timedelta(days=1)).date()


def build() -> None:
    out_dir = REPO / "data" / OUT_SUBDIR
    todo = [
        cfg
        for cfg in CONFIGS
        if not (out_dir / f"{_advance_minus_1(cfg).isoformat()}.xlsx").exists()
    ]
    if not todo:
        print(f"all {len(CONFIGS)} headline vintage(s) already built in {out_dir}")
        return

    specs = load_spec(SPEC_PATHS["baseline"])
    fred = get_fred()
    print(f"fetching {len(specs)} release histories from ALFRED ...")
    histories = {sp.series_id: fetch_release_history(fred, sp.series_id) for sp in specs}
    gdp = histories[TARGET]

    for cfg in todo:
        # Recompute the BEA advance from ALFRED and assert it matches the hand-entered
        # date (first realtime_start of Q's quarter-start GDP observation).
        obs = _quarter_start(cfg.period)
        computed = gdp.loc[gdp["date"] == obs, "realtime_start"].min()
        if pd.isna(computed):
            raise SystemExit(f"{cfg.period}: no GDP observation dated {obs.date()} in ALFRED")
        computed = pd.Timestamp(computed).normalize()
        if computed != pd.Timestamp(cfg.advance_date):
            raise SystemExit(
                f"{cfg.period}: ALFRED advance {computed.date()} != cfg.advance_date "
                f"{cfg.advance_date} -- update QuarterCfg.advance_date"
            )

        as_of = _advance_minus_1(cfg)
        path = write_vintage(build_vintage(histories, specs, as_of), out_dir, as_of)
        print(
            f"{cfg.period}: advance={cfg.advance_date}  "
            f"cutoff(advance-1)={as_of.isoformat()}  -> {path}"
        )


if __name__ == "__main__":
    build()
