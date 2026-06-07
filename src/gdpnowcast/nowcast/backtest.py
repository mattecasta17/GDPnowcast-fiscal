"""Multi-quarter pseudo-real-time backtest driver.

Wraps ``run_quarter`` over the configs/quarters.json registry and collects, per quarter:
the weekly nowcast path, the (advance-1) pre-advance HEADLINE nowcast (Phase 4.0 gate
metric), and the v1-parity skipped vintages.

The 34 quarters are independent, so ``run_backtest`` can fan them out across processes
(``workers>1``) -- each worker runs the unchanged ``run_quarter`` (so the golden numbers are
untouched) and returns a picklable summary. The worker ``_run_one`` is module-level so it
survives the Windows spawn start-method.
"""

from __future__ import annotations

import concurrent.futures as cf
from typing import Any

from .config import CONFIGS
from .runner import run_quarter


def _run_one(period: str, data_subdir: str, spec_file: str, mask_target: bool) -> dict[str, Any]:
    cfg = CONFIGS[period]
    df = run_quarter(cfg, data_subdir=data_subdir, spec_file=spec_file, mask_target=mask_target)
    return {
        "period": period,
        "advance_date": cfg.advance_date,
        "gdp_actual": cfg.gdp_actual,
        "headline": df.attrs.get("headline"),  # {vintage, y_new, error} or None
        "weekly": df.to_dict("records"),  # list of {vintage, y_old, y_new, error, impact_*}
        "skipped": list(df.attrs.get("skipped", [])),
    }


def run_backtest(
    data_subdir: str,
    spec_file: str,
    periods: list[str] | None = None,
    mask_target: bool = False,
    workers: int = 1,
) -> list[dict[str, Any]]:
    """Run every (or a subset of) quarter and return per-quarter summaries, in registry order."""
    todo = list(periods) if periods else list(CONFIGS.keys())
    out: dict[str, dict[str, Any]] = {}
    if workers > 1:
        with cf.ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_run_one, p, data_subdir, spec_file, mask_target): p for p in todo}
            for fut in cf.as_completed(futs):
                r = fut.result()
                out[r["period"]] = r
    else:
        for p in todo:
            out[p] = _run_one(p, data_subdir, spec_file, mask_target)
    return [out[p] for p in todo]
