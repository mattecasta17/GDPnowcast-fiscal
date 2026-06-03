import json
from pathlib import Path

import numpy as np
import pytest

from gdpnowcast.nowcast.config import CONFIG_2017Q1
from gdpnowcast.nowcast.runner import run_quarter

GOLDEN = json.loads(Path("tests/golden/dfm_legacy_nowcast.json").read_text())
RTOL = ATOL = 1e-6

pytestmark = [
    pytest.mark.golden,
    pytest.mark.slow,  # re-estimates prev+curr params (full EM) + 21-pair news loop
    pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent"),
]


def test_run_quarter_reproduces_legacy_2017q1_nowcast() -> None:
    df = run_quarter(
        CONFIG_2017Q1, data_subdir="US_new_v1", spec_file="Spec_US_new.xlsx", series="GDPC1"
    )

    golden_rows = GOLDEN["rows"]

    # The runner must skip the SAME 3 vintages v1's blanket try/except dropped
    # (2016-12-30, 2017-02-24 = no-news weeks; 2017-04-28 = GDP-release week),
    # leaving exactly the 18 golden rows, in order.
    assert list(df["vintage"]) == [r["vintage"] for r in golden_rows]
    assert [v for v in CONFIG_2017Q1.vintages[1:] if v not in set(df["vintage"])] == [
        s["vintage"] for s in GOLDEN["skipped"]
    ]

    for got, want in zip(df.to_dict("records"), golden_rows, strict=True):
        np.testing.assert_allclose(
            got["y_new"], want["y_new"], rtol=RTOL, atol=ATOL, err_msg=f"y_new @ {want['vintage']}"
        )
        np.testing.assert_allclose(
            got["y_old"], want["y_old"], rtol=RTOL, atol=ATOL, err_msg=f"y_old @ {want['vintage']}"
        )
