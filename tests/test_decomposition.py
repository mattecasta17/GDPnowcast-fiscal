from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpnowcast.decomposition import gdp_common_share
from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

pytestmark = [
    pytest.mark.slow,  # full EM on one vintage (~35s); run via `pytest -m "golden or slow"`
    pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent"),
]


def test_common_share_is_nontrivial_when_gdp_observed() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    x, _, _ = load_vintage("data/US_new_v1/2017-01-03.xlsx", spec, pd.Timestamp("2000-01-01"))
    res = dfm(x, spec, 1e-4)
    d = gdp_common_share(x, spec, res, series="GDPC1")
    # The v1 bug forced share_common == 1.0 (resid hardcoded to 0). A real split must NOT.
    assert np.isfinite(d["gdp_common"])
    assert d["share_common"] != pytest.approx(1.0)  # would fail on the v1 resid=0 bug
    assert 0.0 < d["share_common"] < 1.5  # plausible magnitude, not degenerate
