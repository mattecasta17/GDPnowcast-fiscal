"""Diebold-Mariano (1995) test of equal predictive accuracy with the Harvey-Leybourne-Newbold
(1997) small-sample correction.

Rewritten from scratch -- the v1 thesis ran a plain ``scipy.stats.ttest_1samp`` on per-Friday
loss differentials POOLED across quarters (N=652), despite Appendix C claiming HAC (see
``docs/audit/...`` / napkin Domain #3). This module operates on QUARTERLY loss differentials
(one per quarter, T~=30 ex-2020), uses the Newey-West long-run variance for the chosen
horizon, applies the HLN finite-sample correction, and refers the statistic to a Student-t
with T-1 df. HAC beyond the horizon lags is deliberately out of scope (matching the headline
1-step case); ``horizon`` controls the autocovariance truncation.

Convention: ``d_t = loss_a_t - loss_b_t``. mean(d) < 0 => model A has the lower loss (A more
accurate) => negative statistic. Two-sided p-value tests H0: equal accuracy.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class DMResult:
    dm_stat: float  # HLN-corrected DM statistic
    p_value: float  # two-sided, Student-t(df)
    df: int  # T - 1
    n: int  # number of quarters
    mean_loss_diff: float  # mean(loss_a - loss_b)
    horizon: int


def _autocov(d: np.ndarray, k: int) -> float:
    """Biased (divide-by-n) sample autocovariance at lag k -- the DM/Newey-West convention."""
    n = len(d)
    dbar = d.mean()
    return float(np.sum((d[k:] - dbar) * (d[: n - k] - dbar)) / n)


def diebold_mariano(loss_a: Sequence[float], loss_b: Sequence[float], horizon: int = 1) -> DMResult:
    """DM-HLN test on quarterly losses of model A vs model B.

    ``loss_*`` are per-quarter forecast losses (e.g. squared or absolute errors), aligned and
    equal length. ``horizon`` h is the forecast horizon in periods (h=1 for the current-quarter
    headline) -- the long-run variance sums autocovariances through lag h-1.
    """
    a = np.asarray(loss_a, dtype=float)
    b = np.asarray(loss_b, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f"loss arrays must be the same shape, got {a.shape} vs {b.shape}")
    if a.ndim != 1:
        raise ValueError("loss arrays must be 1-D")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    d = a - b
    n = len(d)
    if n < 2:
        raise ValueError("need >= 2 observations")
    dbar = float(d.mean())

    lrv = _autocov(d, 0) + 2.0 * sum(_autocov(d, k) for k in range(1, horizon))
    df = n - 1
    if lrv <= 0:
        # identical (or h-truncation-degenerate) losses: no evidence against equal accuracy.
        return DMResult(0.0, 1.0, df, n, dbar, horizon)

    dm = dbar / np.sqrt(lrv / n)
    h = horizon
    hln_factor = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    dm_corrected = float(dm * hln_factor)
    p_value = float(2.0 * stats.t.sf(abs(dm_corrected), df))
    return DMResult(dm_corrected, p_value, df, n, dbar, horizon)
