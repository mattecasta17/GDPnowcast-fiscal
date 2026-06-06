from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpnowcast.nowcast.config import CONFIG_2017Q1
from gdpnowcast.nowcast.runner import run_quarter

RTOL = ATOL = 1e-6

CUTOFF_VINTAGE = "2017-04-27"  # = CONFIG_2017Q1.advance_date (2017-04-28) - 1 day
_VINTAGE_XLSX = Path("data/US_new") / f"{CUTOFF_VINTAGE}.xlsx"

# The headline runs on the fuller v2 panel (data/US_new) and needs the (advance-1)
# vintage built by tools/build_headline_vintages -- gitignored, so absent in CI and
# fresh clones. Skip (not fail) when missing, mirroring the v1-data-gated heavy tests
# (test_runner_masked.py / test_runner_golden.py). Lives in the `just test-golden`
# slow lane; NOT a `golden` parity test (no v1 oracle for the v2-panel headline).
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _VINTAGE_XLSX.exists(),
        reason="(advance-1) headline vintage not built (run tools/build_headline_vintages)",
    ),
]


def test_run_quarter_headline_2017q1_matches_oracle() -> None:
    df = run_quarter(
        CONFIG_2017Q1,
        data_subdir="US_new",
        spec_file="Spec_US_new.xlsx",
        series="GDPC1",
    )

    head = df.attrs["headline"]
    assert head["vintage"] == CUTOFF_VINTAGE
    # Same literal + tolerance as test_runner_masked.py:47 (single source of truth):
    # on this clean quarter the (advance-1) genuine forecast == Friday+mask ==
    # Thursday-no-mask (cutoff-decision-doc table). This is the first test to
    # exercise the real US_new (v2 panel) headline path (masked/golden use US_new_v1).
    np.testing.assert_allclose(head["y_new"], 2.2461378, rtol=RTOL, atol=ATOL)
    # The runner's error convention is gdp_actual - y_new.
    np.testing.assert_allclose(
        head["error"], CONFIG_2017Q1.gdp_actual - head["y_new"], rtol=RTOL, atol=ATOL
    )


def test_headline_vintage_has_no_lookahead_gdp() -> None:
    # Look-ahead guard: the headline must be a genuine forecast, not a read-back of
    # the advance. GDPC1 at the 2017Q1 target row (2017-03-01, last-month-of-quarter
    # stamping) must be NaN in the (advance-1) vintage. Mirrors
    # release_day_leak_scan._gdp_at_q1.
    df = pd.read_excel(_VINTAGE_XLSX)
    df["Date"] = pd.to_datetime(df["Date"])
    cell = df.loc[df["Date"] == pd.Timestamp("2017-03-01"), "GDPC1"]
    assert not cell.empty
    assert bool(np.isnan(cell.iloc[0]))
