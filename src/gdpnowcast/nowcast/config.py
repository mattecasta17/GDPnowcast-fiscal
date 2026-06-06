"""Backtest configuration for the parameterised nowcast runner.

A ``QuarterCfg`` fully specifies one quarter's pseudo-real-time backtest: the
ordered weekly vintages, the realized GDP advance estimate to score against, and
the prev/curr parameter vintages with the switch date (v1's "parameters fixed
within the quarter, re-estimated at quarter start" logic from nowcast_2017.py).

Only the baseline 2017q1 entry is wired here, to prove the machinery against the
v1 golden. The remaining quarters and the fiscal variant are a Phase-4 addition
(the runner itself is variant-agnostic via its data_subdir/spec_file args).
"""

from __future__ import annotations

from dataclasses import dataclass


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


# Ported verbatim from nowcast_2017.py (vintages_dict["2017q1"], param_map_2017,
# gdp_adv_estimate). v1's opaque pickle params + broken absolute Windows paths are
# gone: run_quarter re-estimates prev/curr from the prev/curr data vintages.
CONFIG_2017Q1 = QuarterCfg(
    period="2017q1",
    vintages=(
        "2016-12-02",
        "2016-12-09",
        "2016-12-16",
        "2016-12-23",
        "2016-12-30",
        "2017-01-06",
        "2017-01-13",
        "2017-01-20",
        "2017-01-27",
        "2017-02-03",
        "2017-02-10",
        "2017-02-17",
        "2017-02-24",
        "2017-03-03",
        "2017-03-10",
        "2017-03-17",
        "2017-03-24",
        "2017-03-31",
        "2017-04-07",
        "2017-04-14",
        "2017-04-21",
        "2017-04-28",
    ),
    gdp_actual=0.7,
    prev_vintage="2016-10-03",
    curr_vintage="2017-01-03",
    switch_date="2017-01-01",
    advance_date="2017-04-28",  # BEA 2017Q1 advance; cutoff vintage = advance-1 = 2017-04-27
)
