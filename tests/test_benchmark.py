"""Phase-4.5 benchmark guards: point-in-time growth series + look-ahead safety + finite forecasts.

The naive benchmarks must forecast the current quarter's growth from ONLY data released by the
(advance-1) cutoff. This pins that: at advance-1 the current quarter's pca(GDPC1) cell is NaN
(unreleased), so it is excluded from the growth series the benchmarks fit on, and every model
returns a finite 1-step forecast. Marked slow (needs the built US_new (advance-1) vintages).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.nowcast.benchmark import BENCHMARKS, benchmark_forecasts, growth_series
from gdpnowcast.nowcast.config import CONFIGS
from gdpnowcast.transform import load_vintage

_QUARTERS = ["2017q1", "2019q1", "2022q1", "2025q1"]


def _advance_minus_1(period: str) -> str:
    return (pd.Timestamp(CONFIGS[period].advance_date) - pd.Timedelta(days=1)).date().isoformat()


def _vintage_file(period: str) -> Path:
    return Path("data") / "US_new" / f"{_advance_minus_1(period)}.xlsx"


def _quarter_end_month(period: str) -> pd.Timestamp:
    year, q = int(period[:4]), int(period[5])
    return pd.Timestamp(year, 3 * (q - 1) + 1, 1) + pd.offsets.MonthBegin(2)


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(_vintage_file(p).exists() for p in _QUARTERS),
        reason="(advance-1) US_new vintages absent (run tools.build_headline_vintages)",
    ),
]


@pytest.mark.parametrize("period", _QUARTERS)
def test_current_quarter_is_unreleased_at_advance_minus_1(period: str) -> None:
    """Look-ahead guard: the target quarter's pca(GDPC1) cell must be NaN at the cutoff."""
    spec = load_dfm_spec("Spec_US_new.xlsx")
    i_gdp = list(spec.series_id).index("GDPC1")
    x, time, _ = load_vintage(str(_vintage_file(period)), spec)
    qend = _quarter_end_month(period)
    rows = [k for k, t in enumerate(time) if t == qend]
    assert rows, f"{period}: quarter-end {qend.date()} not on the monthly grid"
    assert math.isnan(x[rows[0], i_gdp]), (
        f"{period}: current-quarter GDP leaked into advance-1 vintage"
    )


@pytest.mark.parametrize("period", _QUARTERS)
def test_growth_series_excludes_current_quarter_and_forecasts_are_finite(period: str) -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    g = growth_series(str(_vintage_file(period)), spec)
    # The series ends strictly before the current quarter, and has enough history to fit.
    assert g.size >= 4
    assert np.all(np.isfinite(g))
    fc = benchmark_forecasts(g)
    assert set(fc) == set(BENCHMARKS)
    assert all(math.isfinite(v) for v in fc.values())
    # The trivial models are exactly the mean / last observation of that same series.
    assert fc["mean"] == pytest.approx(float(g.mean()))
    assert fc["rw"] == pytest.approx(float(g[-1]))
