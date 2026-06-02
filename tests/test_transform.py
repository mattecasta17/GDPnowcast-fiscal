from pathlib import Path

import numpy as np
import pytest

from Functions.load_data import load_data as v1_load_data
from Functions.load_spec import load_spec as v1_load_spec
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.transform import load_vintage

VINT = "data/US_new_v1/2017-01-03.xlsx"

pytestmark = pytest.mark.skipif(not Path("data/US_new_v1").exists(), reason="v1 data backup absent")


def test_transform_matches_v1_x() -> None:
    x1, _, _ = v1_load_data(VINT, v1_load_spec("Spec_US_new.xlsx"))
    x2, _, _ = load_vintage(VINT, load_dfm_spec("Spec_US_new.xlsx"))
    assert x1.shape == x2.shape
    assert np.array_equal(np.isnan(x1), np.isnan(x2))
    np.testing.assert_allclose(np.nan_to_num(x1), np.nan_to_num(x2), rtol=0, atol=0)
