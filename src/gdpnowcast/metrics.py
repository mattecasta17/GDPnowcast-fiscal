"""Point-forecast error metrics for the headline backtest (RMSE / MAE / Bias).

errors[i] = gdp_advance[i] - headline_nowcast[i] for quarter i (NY-Fed-style "final
pre-advance nowcast vs BEA advance"). Kept deliberately small and dependency-light; the
Diebold-Mariano / HLN significance machinery is a separate module (Phase-4 methodology).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def rmse(errors: Sequence[float]) -> float:
    e = np.asarray(errors, dtype=float)
    return float(np.sqrt(np.mean(e**2)))


def mae(errors: Sequence[float]) -> float:
    e = np.asarray(errors, dtype=float)
    return float(np.mean(np.abs(e)))


def bias(errors: Sequence[float]) -> float:
    """Mean error = mean(advance - nowcast); >0 means the nowcast under-predicts."""
    e = np.asarray(errors, dtype=float)
    return float(np.mean(e))


def summarize(errors: Sequence[float]) -> dict[str, float]:
    return {
        "n": float(len(errors)),
        "rmse": rmse(errors),
        "mae": mae(errors),
        "bias": bias(errors),
    }
