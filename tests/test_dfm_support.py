import numpy as np
import pytest

from Functions.remNaNs_spline import remNaNs_spline as v1_rem_nans_spline
from gdpnowcast._dfm_support import rem_nans_spline


def _synthetic_with_nans() -> np.ndarray:
    """Deterministic T x N panel exercising method-2/3: leading & trailing
    all-NaN rows (row removal) plus interior per-column gaps (spline + filter).
    No column is fully NaN in the kept region, so CubicSpline is well-posed."""
    t, n = 40, 6
    j = np.arange(1, n + 1, dtype=float)
    trend = np.linspace(1.0, 10.0, t)[:, None] * j[None, :]
    seasonal = np.sin(np.arange(t)[:, None] / 3.0 + j[None, :])
    x = trend + seasonal
    x[:2, :] = np.nan  # leading all-NaN rows
    x[-3:, :] = np.nan  # trailing all-NaN rows
    x[10:13, 0] = np.nan  # interior gaps (interpolated by the spline)
    x[5, 1] = np.nan
    x[20:26, 2] = np.nan
    x[7, 3] = np.nan
    x[15, 4] = np.nan
    x[34, 5] = np.nan
    return x


@pytest.mark.parametrize("method", [2, 3])  # the two methods dfm() actually uses
def test_rem_nans_spline_matches_v1(method: int) -> None:
    x = _synthetic_with_nans()
    opts = {"method": method, "k": 3}
    x1, ind1 = v1_rem_nans_spline(x.copy(), opts)
    x2, ind2 = rem_nans_spline(x.copy(), opts)
    assert x1.shape == x2.shape
    assert np.array_equal(ind1, ind2)
    assert np.array_equal(np.isnan(x1), np.isnan(x2))
    np.testing.assert_allclose(np.nan_to_num(x1), np.nan_to_num(x2), rtol=0, atol=0)
