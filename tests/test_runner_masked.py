from pathlib import Path

import numpy as np
import pytest

from gdpnowcast.nowcast.config import CONFIG_2017Q1
from gdpnowcast.nowcast.runner import run_quarter

RTOL = ATOL = 1e-6

# Masked output is NEW behaviour (no v1 oracle), so it is NOT a `golden` parity
# test -- but it is heavy (full-EM run_quarter) and needs the v1 data backup, so
# it shares the `slow` lane (picked up by `just test-golden`).
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent"),
]


def test_run_quarter_masked_2017q1_recovers_release_week() -> None:
    df = run_quarter(
        CONFIG_2017Q1,
        data_subdir="US_new_v1",
        spec_file="Spec_US_new.xlsx",
        series="GDPC1",
        mask_target=True,
    )

    # Release-week vintage (2017-04-28) is no longer dropped: with the target
    # masked it forecasts genuinely instead of reading back the BEA advance.
    assert "2017-04-28" in list(df["vintage"])
    # 18 golden rows + the recovered release-week row.
    assert len(df) == 19
    # Only the two no-news weeks still drop; the release week does not.
    assert df.attrs["skipped"] == ["2016-12-30", "2017-02-24"]

    final = df[df["vintage"] == "2017-04-28"].iloc[0]
    y_new = float(final["y_new"])
    # Genuine forecast, NOT the advance read-back (gdp_actual = 0.7).
    assert np.isfinite(y_new)
    assert abs(y_new - CONFIG_2017Q1.gdp_actual) > 0.1

    # Characterization pin: lock the genuine masked forecast so future refactors
    # can't silently shift it. Value reproduced here (and independently in the design
    # review) to 7 sig figs = the resolution of the 1e-6 tolerance band (+-3.3e-6);
    # numpy rounds the actual to 2.246138, consistent with this pin.
    np.testing.assert_allclose(y_new, 2.2461378, rtol=RTOL, atol=ATOL)
    # The runner's error column is gdp_actual - y_new for the recovered row.
    np.testing.assert_allclose(
        float(final["error"]), CONFIG_2017Q1.gdp_actual - y_new, rtol=RTOL, atol=ATOL
    )
