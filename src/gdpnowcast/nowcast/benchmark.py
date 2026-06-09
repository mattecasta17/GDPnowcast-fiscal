"""Naive univariate benchmarks for the (advance-1) headline GDP nowcast.

These contextualize the DFM: does the dynamic factor model actually beat trivial
time-series models on the *same* target (BEA advance annualized real-GDP growth) at the
*same* (advance-1) pre-advance cutoff? Each benchmark sees only the point-in-time GDPC1
growth series reconstructable from the quarter's (advance-1) vintage -- the current
quarter's GDP level is not yet released there, so its ``pca`` growth cell is NaN and the
forecast is genuinely 1-step-ahead (look-ahead-safe, the same guarantee as the DFM
headline; see ``nowcast/runner.py`` and ``docs/plans/2026-06-04-phase4.0-...-cutoff``).

Models, all re-fit per vintage on the growth observed at that cutoff:
  * ``mean``   -- unconditional sample mean of observed growth (the no-dynamics floor)
  * ``rw``     -- random walk: last observed quarter's growth
  * ``ar1``    -- AR(1) with constant  (ARIMA order (1,0,0))
  * ``arma11`` -- ARMA(1,1) with constant  (ARIMA order (1,0,1))

The ARMA family is the Phase-4.5 benchmark named in the roadmap; mean/rw are added as
near-zero-cost trivial floors. GDPNow is intentionally NOT included -- it has no clean
ALFRED point-in-time vintage history, so a pseudo-real-time replay would not be honest
(documented in ``tools/run_benchmarks.py`` / the results write-up).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from ..dfm_spec import DfmSpec
from ..transform import load_vintage

# Match the DFM estimation window (runner._SAMPLE_START) so the benchmarks see the same
# information span -- a fair "same data, simpler model" comparison.
SAMPLE_START = pd.Timestamp("2000-01-01")

BENCHMARKS = ("mean", "rw", "ar1", "arma11")
_ORDER = {"ar1": (1, 0, 0), "arma11": (1, 0, 1)}


def growth_series(
    vintage_file: str,
    spec: DfmSpec,
    series: str = "GDPC1",
    sample_start: pd.Timestamp | None = None,
) -> np.ndarray:
    """Point-in-time annualized-growth series of ``series`` from one (advance-1) vintage.

    Returns the non-NaN ``pca``-transformed quarter-end values, in chronological order. The
    current quarter is excluded by construction (its level is unreleased at advance-1).
    """
    i = list(spec.series_id).index(series)
    start = SAMPLE_START if sample_start is None else sample_start
    x, _, _ = load_vintage(vintage_file, spec, start)
    g = x[:, i]
    return g[~np.isnan(g)].astype(float)


def _arima_forecast(g: np.ndarray, order: tuple[int, int, int]) -> float:
    # Short quarterly series + MLE: convergence / non-stationary-start warnings are expected
    # and benign (the point forecast is still the MLE one-step mean). Silence them for clean runs.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from statsmodels.tsa.arima.model import ARIMA  # local import: heavy, only needed here

        res = ARIMA(g, order=order, trend="c").fit()
        return float(np.asarray(res.forecast(1))[0])


def benchmark_forecasts(g: np.ndarray) -> dict[str, float]:
    """One-step-ahead forecast of next-quarter growth from each benchmark, given history ``g``."""
    if g.size < 4:
        raise ValueError(f"need >= 4 growth observations to fit benchmarks, got {g.size}")
    out = {"mean": float(g.mean()), "rw": float(g[-1])}
    for name, order in _ORDER.items():
        out[name] = _arima_forecast(g, order)
    return out
