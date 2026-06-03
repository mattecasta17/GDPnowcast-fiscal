"""Parameterised pseudo-real-time nowcast backtest runner.

Replaces v1's 18 near-duplicate ``nowcast_YYYY*.py`` scripts with one
config-driven ``run_quarter`` loop.
"""

from .config import CONFIG_2017Q1, QuarterCfg
from .runner import run_quarter

__all__ = ["CONFIG_2017Q1", "QuarterCfg", "run_quarter"]
