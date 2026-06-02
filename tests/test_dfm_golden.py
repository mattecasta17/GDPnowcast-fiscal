import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_estimator.json").read_text())
RTOL = ATOL = 1e-6  # A2 pickle_max_abs_dC ~= 5e-15 justified the tight default
SAMPLE_START = pd.Timestamp("2000-01-01")

pytestmark = [
    pytest.mark.golden,
    pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent"),
]


@pytest.mark.parametrize("vintage", list(GOLDEN["vintages"]))
def test_dfm_matches_legacy_golden(vintage: str) -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    x, _, _ = load_vintage(f"data/US_new_v1/{vintage}.xlsx", spec, SAMPLE_START)
    res = dfm(x, spec, GOLDEN["meta"]["threshold"])
    g = GOLDEN["vintages"][vintage]
    assert res["C"].shape[0] == g["n_series"] == 28
    np.testing.assert_allclose(res["loglik"][-1], g["loglik_final"], rtol=RTOL, atol=ATOL)
    for key in ("C", "A", "Q", "R", "Z_0", "V_0", "Mx", "Wx"):
        np.testing.assert_allclose(np.asarray(res[key]), np.asarray(g[key]), rtol=RTOL, atol=ATOL)
    i_gdp = int(np.where(spec.series_id == "GDPC1")[0][0])
    np.testing.assert_allclose(
        np.asarray(res["x_sm"])[-6:, i_gdp], np.asarray(g["x_sm_gdp_tail"]), rtol=RTOL, atol=ATOL
    )
