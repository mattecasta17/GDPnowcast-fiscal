"""Fiscal-block ablation: headline-only (advance-1) backtest for M1/M2/M3.

Self-contained analysis script (lives under ablation/, NOT part of the package).
For each model spec it computes ONLY the (advance-1) pre-advance headline nowcast per
quarter -- i.e. a single DFM re-estimation per quarter (no weekly walk), mirroring the
headline branch of nowcast.runner.run_quarter. All variants read the SAME US_fiscal data
panel; the only thing that changes is which fiscal series the spec activates (Model==1):

  M1 deficit-only   = macro + MTSDS133FMS
  M2 deficit+income = macro + MTSDS133FMS + W875RX1
  M3 deficit+govt   = macro + MTSDS133FMS + GCEC1

(M0 macro-only == docs/dashboard_data/baseline.json, M4 all-three == fiscal.json -- not rerun.)

Windows-spawn safe: the worker (_headline_one) is module-level and main() is guarded by
``if __name__ == "__main__"`` (mirrors src/.../nowcast/backtest.py). Each quarter is wrapped
so one bad quarter logs and continues instead of killing the run.

Usage (from repo root):
  uv run python ablation/run_ablation.py            # full: M1,M2,M3 x 34 quarters
  uv run python ablation/run_ablation.py --smoke    # 2 quarters of M1 only (pipeline check)
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import time
from pathlib import Path

import pandas as pd

from gdpnowcast.dfm import dfm
from gdpnowcast.dfm_spec import load_dfm_spec
from gdpnowcast.news import nowcast_point
from gdpnowcast.nowcast.config import CONFIGS
from gdpnowcast.transform import load_vintage

REPO = Path(__file__).resolve().parents[1]
ABL = REPO / "ablation"
SAMPLE_START = pd.Timestamp("2000-01-01")
DATA_SUBDIR = "US_fiscal"
SERIES = "GDPC1"

MODELS = {
    "M1_deficit_only": str(ABL / "Spec_M1_deficit_only.xlsx"),
    "M2_deficit_income": str(ABL / "Spec_M2_deficit_income.xlsx"),
    "M3_deficit_govt": str(ABL / "Spec_M3_deficit_govt.xlsx"),
}


def _vfile(v: str) -> str:
    return str(REPO / "data" / DATA_SUBDIR / f"{v}.xlsx")


def _headline_one(period: str, spec_file: str) -> dict:
    """One quarter's (advance-1) headline nowcast under the given spec.

    Mirrors runner.run_quarter's headline branch: res_head == res_curr because the
    (advance-1) cutoff always falls within the target quarter (>= the quarter-start
    switch), so only res_curr is needed (one DFM estimation)."""
    cfg = CONFIGS[period]
    adv_minus_1 = (pd.Timestamp(cfg.advance_date) - pd.Timedelta(days=1)).date().isoformat()
    hf = Path(_vfile(adv_minus_1))
    if pd.Timestamp(adv_minus_1) < pd.Timestamp(cfg.switch_date):
        return {"period": period, "headline": None, "error": None, "reason": "adv-1 < switch"}
    if not hf.exists():
        return {"period": period, "headline": None, "error": None, "reason": "no cutoff vintage"}
    try:
        spec = load_dfm_spec(spec_file)
        res_curr = dfm(load_vintage(_vfile(cfg.curr_vintage), spec, SAMPLE_START)[0], spec, 1e-4)
        xh, timeh, _ = load_vintage(str(hf), spec)
        y = float(nowcast_point(xh, timeh, spec, res_curr, SERIES, cfg.period))
        return {
            "period": period,
            "headline": y,
            "error": cfg.gdp_actual - y,
            "gdp_actual": cfg.gdp_actual,
            "cutoff": adv_minus_1,
        }
    except Exception as e:
        return {"period": period, "headline": None, "error": None, "reason": repr(e)}


def _run_model(name: str, spec_file: str, periods: list[str], workers: int) -> list[dict]:
    t0 = time.time()
    print(f"=== {name} === {len(periods)} quarters, {workers} workers", flush=True)
    res: dict[str, dict] = {}
    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_headline_one, p, spec_file): p for p in periods}
        done = 0
        for fut in cf.as_completed(futs):
            r = fut.result()
            res[r["period"]] = r
            done += 1
            tag = r["headline"] if r["headline"] is not None else f"SKIP({r.get('reason')})"
            print(f"  [{done}/{len(periods)}] {r['period']}: {tag}", flush=True)
    print(f"  {name} done in {time.time() - t0:.0f}s", flush=True)
    return [res[p] for p in periods]


def main() -> None:
    smoke = "--smoke" in sys.argv
    all_periods = list(CONFIGS.keys())
    if smoke:
        out = {
            "M1_deficit_only": _run_model(
                "M1_deficit_only", MODELS["M1_deficit_only"], all_periods[:2], 2
            )
        }
        (ABL / "ablation_smoke.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("WROTE ablation/ablation_smoke.json", flush=True)
        return
    out = {name: _run_model(name, spec, all_periods, 4) for name, spec in MODELS.items()}
    (ABL / "ablation_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("WROTE ablation/ablation_results.json", flush=True)


if __name__ == "__main__":
    main()
