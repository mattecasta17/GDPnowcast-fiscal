"""DFM support helpers — typed port of the v1 Functions/ modules the DFM core
imports. Currently `rem_nans_spline` (port of Functions/remNaNs_spline.py): NaN
handling for the EM/Kalman pipeline. Numerically identical to v1 on the methods
the estimator uses (tests/test_dfm_support.py, method 2 & 3).

Only the module the estimator actually imports is ported here. The standalone
Functions/decompose_common_factor.py is intentionally NOT ported: nothing in the
pipeline imports it, and the honest GDP common/residual split lives in
decomposition.py (B6)."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import lfilter


def rem_nans_spline(X: np.ndarray, options: dict) -> tuple[np.ndarray, np.ndarray]:
    """Treat NaNs in the data matrix X for use in the DFM (port of v1
    remNaNs_spline). `options` carries `method` (1-5) and `k` (filter half-width).
    Returns the processed X and the boolean NaN-location mask `indNaN`.

    Methods:
      1: replace all missing values with a moving-average filter.
      2: replace missing values after removing leading/trailing all-NaN rows
         (a row is dropped if >80% NaN); interior gaps cubic-splined.
      3: only remove rows with leading/trailing all-NaN values.
      4: like 2 but a row is dropped only if ALL values are NaN.
      5: replace missing values (spline then filter) without removing rows.

    The stray per-column `print(i)` debug line from v1's method-2 branch is
    dropped (output-only; no numerical effect)."""
    T, N = X.shape
    k = options["k"]
    indNaN = np.isnan(X)

    if options["method"] == 1:  # replace all the missing values
        for i in range(N):  # Loop through columns
            x = X[:, i].copy()
            x[indNaN[:, i]] = np.nanmedian(x)
            x_MA = lfilter(
                np.ones(2 * k + 1) / (2 * k + 1),
                1,
                np.append(np.append(x[0] * np.ones((k, 1)), x), x[-1] * np.ones((k, 1))),
            )
            x_MA = x_MA[(2 * k + 1) - 1 :]  # Match dimensions
            x[indNaN[:, i]] = x_MA[indNaN[:, i]]
            X[:, i] = x  # Replace vector

    elif options["method"] == 2:  # remove leading/trailing all-NaN rows, then fill
        # Row sum of NaNs; mark rows with more than 80% NaN.
        rem1 = np.nansum(indNaN, axis=1) > (N * 0.8)
        nanLead = np.cumsum(rem1) == np.arange(1, (T + 1))
        nanEnd = np.cumsum(rem1) == np.arange(T, 0, -1)
        nanLE = nanLead | nanEnd

        X = X[~nanLE, :]
        indNaN = np.isnan(X)

        for i in range(N):  # Loop for each series
            x = X[:, i].copy()
            isnanx = np.isnan(x)
            t1 = np.min(np.where(~isnanx))  # First non-NaN entry
            t2 = np.max(np.where(~isnanx))  # Last non-NaN entry

            # Interpolate interior NaNs (leaves leading/trailing NaNs in place).
            x[t1 : t2 + 1] = CubicSpline(np.where(~isnanx)[0], x[~isnanx])(np.arange(t1, t2 + 1))
            isnanx = np.isnan(x)

            # Replace remaining NaNs with the median, then moving-average filter.
            x[isnanx] = np.nanmedian(x)
            x_MA = lfilter(
                np.ones(2 * k + 1) / (2 * k + 1),
                1,
                np.append(np.append(x[0] * np.ones((k, 1)), x), x[-1] * np.ones((k, 1))),
            )
            x_MA = x_MA[(2 * k + 1) - 1 :]
            x[isnanx] = x_MA[isnanx]
            X[:, i] = x

    elif options["method"] == 3:
        rem1 = np.sum(indNaN, axis=1) == N
        nanLead = np.cumsum(rem1) == np.arange(1, (T + 1))
        nanEnd = np.cumsum(rem1) == np.arange(T, 0, -1)
        nanLE = nanLead | nanEnd

        X = X[~nanLE, :]
        indNaN = np.isnan(X)

    elif options["method"] == 4:  # remove all-NaN rows & replace missing values
        rem1 = np.sum(indNaN, axis=1) == N
        nanLead = np.cumsum(rem1) == np.arange(1, (T + 1))
        nanEnd = np.cumsum(rem1) == np.arange(T, 0, -1)
        nanLE = nanLead | nanEnd

        X = X[~nanLE, :]
        indNaN = np.isnan(X)

        for i in range(N):
            x = X[:, i].copy()
            isnanx = np.isnan(x)
            t1 = np.min(np.where(~isnanx))
            t2 = np.max(np.where(~isnanx))
            x[t1 : t2 + 1] = CubicSpline(np.where(~isnanx)[0], x[~isnanx])(np.arange(t1, t2 + 1))
            isnanx = np.isnan(x)
            x[isnanx] = np.nanmedian(x)
            x_MA = lfilter(
                np.ones(2 * k + 1) / (2 * k + 1),
                1,
                np.append(np.append(x[0] * np.ones((k, 1)), x), x[-1] * np.ones((k, 1))),
            )
            x_MA = x_MA[(2 * k + 1) - 1 :]
            x[isnanx] = x_MA[isnanx]
            X[:, i] = x

    elif options["method"] == 5:  # replace missing values, keep all rows
        indNaN = np.isnan(X)

        for i in range(N):
            x = X[:, i].copy()
            isnanx = np.isnan(x)
            t1 = np.min(np.where(~isnanx))
            t2 = np.max(np.where(~isnanx))
            x[t1 : t2 + 1] = CubicSpline(np.where(~isnanx)[0], x[~isnanx])(np.arange(t1, t2 + 1))
            isnanx = np.isnan(x)
            x[isnanx] = np.nanmedian(x)
            x_MA = lfilter(
                np.ones(2 * k + 1) / (2 * k + 1),
                1,
                np.append(np.append(x[0] * np.ones((k, 1)), x), x[-1] * np.ones((k, 1))),
            )
            x_MA = x_MA[(2 * k + 1) - 1 :]
            x[isnanx] = x_MA[isnanx]
            X[:, i] = x

    return X, indNaN
