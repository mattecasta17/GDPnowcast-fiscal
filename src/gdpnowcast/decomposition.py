"""Honest GDP common-component share at the latest *observed* GDP period.

Replaces ``Functions/extract_common_residual.py``, which hardcoded the residual
to ``0.0`` (so ``share_common`` was tautologically ``1.0``/``NaN`` and carried no
information). Here the residual is the genuine one-step **projection** residual
``observed - C·f`` (de-standardised): ``C·f`` is the Kalman *prior* (one-step
forecast) of the observation, and the residual is the forecast error.

Two correctness fixes over the v1 module (both inherited by the literal plan
snippet, both consistent with this module's documented intent):
  1. The Kalman filter operates in **standardised** space, so the data is
     standardised with the model's ``Mx``/``Wx`` before ``SKF`` — v1 fed the raw
     transformed data, putting the factors on the wrong scale.
  2. The share is evaluated at the latest period where GDP is **observed**, not
     the literal last row (GDP is quarterly, so the last monthly row is ``NaN``
     and would force the degenerate ``share_common == 1.0`` the test guards).

NOTE: this is the one-step projection residual, NOT the model's idiosyncratic
AR(1) state. The full state-based common/idiosyncratic decomposition is a
Phase 7 deliverable; Phase 3 ships only this honest, non-degenerate split.
"""

from __future__ import annotations

import numpy as np

from .dfm import SKF
from .dfm_spec import DfmSpec


def gdp_common_share(x: np.ndarray, spec: DfmSpec, res: dict, series: str = "GDPC1") -> dict:
    """Common-factor share of ``series`` at its latest observed period.

    Parameters
    ----------
    x
        Transformed (NOT standardised) data, ``(T, N)`` or ``(N, T)``; the same
        matrix passed to :func:`gdpnowcast.dfm.dfm`.
    spec
        The loaded :class:`DfmSpec` (for ``series_id`` lookup).
    res
        The ``dict`` returned by :func:`gdpnowcast.dfm.dfm` (uses ``A C Q R Z_0
        V_0 Mx Wx``).
    series
        Series id to decompose (default GDP).

    Returns
    -------
    dict with ``series``, ``gdp_total`` (observed), ``gdp_common`` (one-step
    forecast), ``gdp_proj_residual`` (= total - common) and ``share_common``.
    """
    n = res["C"].shape[0]
    xt = x.T if x.shape[0] != n else x  # -> (N, T)
    mx = np.asarray(res["Mx"]).reshape(-1)
    wx = np.asarray(res["Wx"]).reshape(-1)
    xn = (xt - mx[:, None]) / wx[:, None]  # standardise to the space C/A/... live in

    i = int(np.where(np.asarray(spec.series_id) == series)[0][0])
    observed = np.where(~np.isnan(xn[i, :]))[0]
    if observed.size == 0:  # series never observed: no forecast error to measure
        t = xn.shape[1] - 1
        f = SKF(xn, res["A"], res["C"], res["Q"], res["R"], res["Z_0"], res["V_0"])["Zm"][:, t]
        common = float(np.dot(res["C"][i, :], f)) * wx[i] + mx[i]
        return {
            "series": series,
            "gdp_total": common,
            "gdp_common": common,
            "gdp_proj_residual": 0.0,
            "share_common": np.nan,
        }

    t = int(observed[-1])  # latest period where the series is actually observed
    f = SKF(xn, res["A"], res["C"], res["Q"], res["R"], res["Z_0"], res["V_0"])["Zm"][:, t]
    common = float(np.dot(res["C"][i, :], f)) * wx[i] + mx[i]  # de-standardised forecast
    total = float(xn[i, t]) * wx[i] + mx[i]  # de-standardised observed
    resid = total - common
    return {
        "series": series,
        "gdp_total": total,
        "gdp_common": common,
        "gdp_proj_residual": resid,
        "share_common": np.nan if total == 0 else common / total,
    }
