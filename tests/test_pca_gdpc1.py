"""Convention guard: pca(GDPC1) must reproduce the BEA-published advance Q/Q annualized growth.

The DFM ingests GDPC1 via the ``pca`` transform = ((L_Q / L_{Q-1})**4 - 1)*100, stamped on the
LAST month of the quarter (rows 2, 5, 8, ... -- see napkin Domain #1). This pins that
convention: an off-by-one in the quarterly indexing, a wrong annualization exponent, or a
dropped quarter-end stamp would move the value far more than the 0.05 pp tolerance. Empirically
the gap to the (1-decimal) BEA advance is <= 0.038 pp across 2017-2025 incl. the COVID extreme.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.nowcast.config import CONFIGS
from gdpnowcast.transform import load_vintage

pytestmark = pytest.mark.skipif(
    not Path("data/US_new").exists(), reason="US_new panel absent (rebuild via gdpnowcast fetch)"
)

# Quarters whose LAST weekly vintage carries the just-released advance GDP. Excludes the
# 2018-19 shutdown-delayed 2018q4 (its last weekly precedes the advance, so GDP is still NaN).
_QUARTERS = [
    "2017q1",
    "2018q1",
    "2019q1",
    "2020q3",
    "2021q1",
    "2022q4",
    "2023q1",
    "2024q1",
    "2025q1",
]


def _quarter_end_month(period: str) -> pd.Timestamp:
    year, q = int(period[:4]), int(period[5])
    return pd.Timestamp(year, 3 * (q - 1) + 1, 1) + pd.offsets.MonthBegin(2)


@pytest.mark.parametrize("period", _QUARTERS)
def test_pca_gdpc1_matches_bea_advance(period: str) -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    i_gdp = list(spec.series_id).index("GDPC1")
    cfg = CONFIGS[period]
    x, time, _ = load_vintage(f"data/US_new/{cfg.vintages[-1]}.xlsx", spec)
    qend = _quarter_end_month(period)
    rows = [k for k, t in enumerate(time) if t == qend]
    assert rows, f"{period}: quarter-end {qend.date()} not in vintage {cfg.vintages[-1]}"
    assert x[rows[0], i_gdp] == pytest.approx(cfg.gdp_actual, abs=0.05)
