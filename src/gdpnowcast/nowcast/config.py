"""Backtest configuration for the parameterised nowcast runner.

A ``QuarterCfg`` fully specifies one quarter's pseudo-real-time backtest: the ordered
weekly vintages, the realized GDP advance estimate to score against, the prev/curr
parameter vintages with the switch date (v1's "parameters fixed within the quarter,
re-estimated at quarter start" logic), and the BEA advance date (for the (advance-1)
pre-advance headline cutoff -- Phase 4.0 gate decision).

The 34-quarter registry (2017q1-2025q2) is generated from the v1 ``nowcast_YYYY.py``
scripts (calendar + prev/curr/switch) plus ALFRED (advance dates) by
``tools/gen_quarter_configs.py`` and committed as ``configs/quarters.json`` -- the vintage
lists ARE configuration, like ``configs/vintages_*.csv``. The baseline scripts are the
canonical calendar (the one v1 fiscal typo, 2017q3, is dropped in favour of the baseline
Friday); the runner is variant-agnostic via its ``data_subdir``/``spec_file`` args, so one
registry serves both the baseline and fiscal variants.

Advance dates come from ALFRED (first ``realtime_start`` of each quarter-start GDPC1 obs),
so calendar quirks are real, not assumed -- e.g. 2018q4's advance is 2019-02-28 (delayed by
the 2018-19 government shutdown), not the usual late-January date.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
_QUARTERS_JSON = _REPO / "configs" / "quarters.json"


@dataclass(frozen=True)
class QuarterCfg:
    """One quarter's backtest specification (ported from the v1 per-year scripts)."""

    period: str  # nowcast target, e.g. "2017q1"
    vintages: tuple[str, ...]  # ordered weekly vintage dates (ISO strings)
    gdp_actual: float  # advance-estimate GDP growth the nowcasts are scored against
    prev_vintage: str  # data vintage whose params are used before switch_date
    curr_vintage: str  # data vintage whose params are used from switch_date on
    switch_date: str  # quarter-start re-estimation boundary (ISO string)
    advance_date: str  # real BEA advance date = first ALFRED realtime_start of Q's GDP (ISO)


def _load_registry() -> dict[str, QuarterCfg]:
    raw: dict[str, dict[str, Any]] = json.loads(_QUARTERS_JSON.read_text(encoding="utf-8"))
    return {
        period: QuarterCfg(
            period=period,
            vintages=tuple(entry["vintages"]),
            gdp_actual=float(entry["gdp_actual"]),
            prev_vintage=entry["prev_vintage"],
            curr_vintage=entry["curr_vintage"],
            switch_date=entry["switch_date"],
            advance_date=entry["advance_date"],
        )
        for period, entry in raw.items()
    }


# Chronologically ordered period -> QuarterCfg (2017q1 .. 2025q2).
CONFIGS: dict[str, QuarterCfg] = _load_registry()

# Back-compat alias: the first wired quarter, still referenced by the build tool and the
# golden/headline tests as the v1-parity fixture.
CONFIG_2017Q1 = CONFIGS["2017q1"]
