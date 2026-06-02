import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.news import update_nowcast
from gdpnowcast.transform import load_vintage

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_nowcast.json").read_text())
RTOL = ATOL = 1e-6
SAMPLE_START = pd.Timestamp("2000-01-01")
SWITCH = pd.Timestamp("2017-01-01")  # < SWITCH uses prev params, else curr (matches the freeze)

pytestmark = [
    pytest.mark.golden,
    pytest.mark.slow,  # full EM + 18-vintage news smoothing (~6 min); run via `pytest -m golden`
    pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent"),
]


def _v(v: str) -> str:
    return f"data/US_new_v1/{v}.xlsx"


def test_news_matches_legacy_nowcast_golden() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    # Params estimated once with sample_start=2000 (production); reused across vintages.
    res_prev = dfm(load_vintage(_v("2016-10-03"), spec, SAMPLE_START)[0], spec, 1e-4)
    res_curr = dfm(load_vintage(_v("2017-01-03"), spec, SAMPLE_START)[0], spec, 1e-4)

    for row in GOLDEN["rows"]:
        v_old, v_new = (
            row["vintage_old"],
            row["vintage"],
        )  # recorded pairing (non-contiguous after skips)
        res_use = res_prev if pd.Timestamp(v_new) < SWITCH else res_curr
        x_old, _, _ = load_vintage(_v(v_old), spec)  # news step: FULL sample (no sample_start)
        x_new, time, _ = load_vintage(_v(v_new), spec)
        out = update_nowcast(x_old, x_new, time, spec, res_use, "GDPC1", "2017q1", v_old, v_new)
        np.testing.assert_allclose(
            float(out["y_new"][0]), row["y_new"], rtol=RTOL, atol=ATOL, err_msg=f"y_new @ {v_new}"
        )
        np.testing.assert_allclose(
            float(out["y_old"][0]), row["y_old"], rtol=RTOL, atol=ATOL, err_msg=f"y_old @ {v_new}"
        )
