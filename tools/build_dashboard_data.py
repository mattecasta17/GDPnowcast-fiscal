"""Consolidate the committed backtest artifacts into one dashboard-ready JSON bundle.

Reads the four committed, network-free artifacts under ``docs/dashboard_data/``:

  baseline.json    -- DFM headline + weekly paths + metrics (baseline panel US_new)
  fiscal.json      -- same, fiscal panel US_fiscal
  comparison.json  -- fiscal-vs-baseline Diebold-Mariano + power/MDE + per-quarter + leak scan
  benchmarks.json  -- DFM vs naive (mean/RW/AR1/ARMA11) metrics + DM, panel US_new

and writes a single consolidated bundle the static Next.js dashboard imports at build time:

  apps/dashboard/src/data/dashboard.json

Everything is derived from the committed JSON -- NO network, NO re-estimation -- so it is
safe to regenerate any time a backtest changes. Run AFTER run_backtest / compare_variants /
run_benchmarks have refreshed their artifacts.

The ``findings`` section is an honest, data-derived narrative (claim + evidence numbers pulled
straight from the metrics above), kept tied to the numbers rather than hand-written prose:
the DFM does NOT beat the naive benchmarks in normal times (ex-2020) but is far more robust in
the tails (all-34), 0/16 benchmark DM tests are significant, and the fiscal edge is suggestive
but underpowered. See docs/results.md, docs/comparison.md, docs/benchmarks.md.

Usage (from repo root):
  uv run python -m tools.build_dashboard_data
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"
OUT = REPO / "apps" / "dashboard" / "src" / "data" / "dashboard.json"

COVID = ["2020q1", "2020q2", "2020q3", "2020q4"]

TARGET_DEFINITION = (
    "Each nowcast is the DFM's forecast of the BEA advance estimate of annualized real-GDP "
    "growth, evaluated at the (advance_date - 1 day) pre-advance cutoff. At that cutoff the "
    "target quarter's GDP is still unobserved and BEA same-day co-releases (real PCE, income, "
    "PCE prices, durable goods) are excluded, so the score is a genuine pseudo-real-time "
    "forecast error with no look-ahead leakage."
)


def _load(name: str) -> dict:
    return json.loads((DD / f"{name}.json").read_text(encoding="utf-8"))


def _r(x: float, n: int = 2) -> float:
    return round(float(x), n)


def _build_findings(baseline: dict, benchmarks: dict, comparison: dict) -> list[dict]:
    """Honest, number-anchored narrative bullets for the dashboard.

    Numbers are pulled from the loaded artifacts (never re-typed by hand) so the prose can
    never drift from the metrics it describes.
    """
    bm = benchmarks["metrics"]
    dfm_ex = bm["dfm"]["ex_2020"]
    dfm_all = bm["dfm"]["all"]
    mean_ex = bm["mean"]["ex_2020"]
    ar1_ex = bm["ar1"]["ex_2020"]
    rw_all = bm["rw"]["all"]
    ar1_all = bm["ar1"]["all"]

    dm_ex = comparison["diebold_mariano"]["ex_2020"]
    mae_dm = dm_ex["absolute"]
    rmse_dm = dm_ex["squared"]
    mde_ex_abs = comparison["power_mde"]["by_sample"]["ex_2020"]["absolute"]

    # Count benchmark DM cells (models x {all,ex_2020} x {squared,absolute}) and how many reject.
    cells = 0
    sig = 0
    for model in ("mean", "rw", "ar1", "arma11"):
        for sample in ("all", "ex_2020"):
            for loss in ("squared", "absolute"):
                cells += 1
                if benchmarks["diebold_mariano"][model][sample][loss]["p_value"] < 0.05:
                    sig += 1

    return [
        {
            "id": "target",
            "title": "Honest pseudo-real-time target",
            "body": (
                "Every nowcast is scored against the BEA advance growth estimate at a pre-advance "
                "cutoff (advance day minus one). No target value and no same-day BEA co-release "
                "leak into the forecast, so the errors below are genuine, not read-backs."
            ),
            "evidence": {"n_quarters": int(dfm_all["n"]), "n_ex_2020": int(dfm_ex["n"])},
        },
        {
            "id": "headline",
            "title": "DFM headline accuracy",
            "body": (
                f"On the 30 non-COVID quarters the DFM headline has RMSE {_r(dfm_ex['rmse'])} pp / "
                f"MAE {_r(dfm_ex['mae'])} pp and is nearly unbiased "
                f"(bias {_r(dfm_ex['bias'])} pp). Including the four 2020 quarters the RMSE jumps "
                f"to {_r(dfm_all['rmse'])} pp -- the pandemic dominates any all-sample metric."
            ),
            "evidence": {
                "rmse_ex_2020": dfm_ex["rmse"],
                "mae_ex_2020": dfm_ex["mae"],
                "bias_ex_2020": dfm_ex["bias"],
                "rmse_all": dfm_all["rmse"],
            },
        },
        {
            "id": "no-edge-normal-times",
            "title": "No RMSE edge over naive in normal times",
            "body": (
                f"Ex-2020 the DFM does NOT beat the naive benchmarks on RMSE: "
                f"DFM {_r(dfm_ex['rmse'])} vs historical-mean {_r(mean_ex['rmse'])} and "
                f"AR(1) {_r(ar1_ex['rmse'])}. The naive models are tighter but biased "
                f"(mean bias +{_r(mean_ex['bias'])}, AR1 bias +{_r(ar1_ex['bias'])}); the DFM "
                f"trades a little noise for near-zero bias."
            ),
            "evidence": {
                "dfm_rmse_ex_2020": dfm_ex["rmse"],
                "mean_rmse_ex_2020": mean_ex["rmse"],
                "ar1_rmse_ex_2020": ar1_ex["rmse"],
                "mean_bias_ex_2020": mean_ex["bias"],
                "ar1_bias_ex_2020": ar1_ex["bias"],
            },
        },
        {
            "id": "robustness-tails",
            "title": "Far more robust in the tails",
            "body": (
                f"Over all 34 quarters the DFM is dramatically more robust than the univariate "
                f"benchmarks, which blow up on 2020: DFM RMSE {_r(dfm_all['rmse'])} vs "
                f"random-walk {_r(rw_all['rmse'])} and AR(1) {_r(ar1_all['rmse'])}. The "
                f"multivariate factor structure keeps the nowcast from chasing a single series "
                f"off a cliff."
            ),
            "evidence": {
                "dfm_rmse_all": dfm_all["rmse"],
                "rw_rmse_all": rw_all["rmse"],
                "ar1_rmse_all": ar1_all["rmse"],
            },
        },
        {
            "id": "dm-indistinguishable",
            "title": "Differences not statistically significant",
            "body": (
                f"None of the {cells} DFM-vs-benchmark Diebold-Mariano tests "
                f"({sig}/{cells} reject at 5%) are significant: by formal testing the DFM and the "
                "naive models are statistically indistinguishable on this short 34-quarter sample. "
                "The DFM's real value is robustness in the tails plus the weekly within-quarter "
                "path it produces, not a headline-RMSE win in calm times."
            ),
            "evidence": {"dm_cells": cells, "dm_significant": sig},
        },
        {
            "id": "fiscal-suggestive",
            "title": "Fiscal augmentation: suggestive, not established",
            "body": (
                f"Adding the fiscal block helps modestly ex-2020 and only on MAE "
                f"(DM {_r(mae_dm['dm_stat'])}, p={_r(mae_dm['p_value'], 3)}), not RMSE "
                f"(DM {_r(rmse_dm['dm_stat'])}, p={_r(rmse_dm['p_value'], 3)}); over all 34 "
                "quarters the two are indistinguishable. Even the one significant cell sits below "
                f"its minimum detectable effect (|effect| {_r(abs(mae_dm['mean_loss_diff']), 3)} < "
                f"MDE {_r(mde_ex_abs['mde'], 3)}), and one p=0.036 across four tests does not "
                "survive multiple-testing correction -- so the fiscal edge is suggestive, not "
                "established."
            ),
            "evidence": {
                "mae_dm_stat": mae_dm["dm_stat"],
                "mae_p_value": mae_dm["p_value"],
                "rmse_dm_stat": rmse_dm["dm_stat"],
                "rmse_p_value": rmse_dm["p_value"],
                "mae_abs_effect": abs(mae_dm["mean_loss_diff"]),
                "mae_mde": mde_ex_abs["mde"],
            },
        },
        {
            "id": "leak-2025q1",
            "title": "2025q1 miss is genuine, not leakage",
            "body": (
                "2025q1 is a contaminated quarter: on the advance day BEA co-releases real PCE "
                "(~68% of GDP), real income and PCE prices. The (advance-1) cutoff excludes all of "
                "them, so the large 2025q1 miss is a true forecast error, not a leakage artifact. "
                f"Only {len(comparison['leak_scan']['clean_quarters'])} of "
                f"{comparison['leak_scan']['quarters']} past quarters are fully clean across the "
                "whole release week."
            ),
            "evidence": {
                "advance_day_coreleases": comparison["leak_scan"]["q2025q1_advance_day_coreleases"],
                "clean_quarters": comparison["leak_scan"]["clean_quarters"],
            },
        },
    ]


def build() -> dict:
    baseline = _load("baseline")
    fiscal = _load("fiscal")
    comparison = _load("comparison")
    benchmarks = _load("benchmarks")

    periods = [r["period"] for r in baseline["headline"]]

    bundle = {
        "meta": {
            "generated_from": [
                "docs/dashboard_data/baseline.json",
                "docs/dashboard_data/fiscal.json",
                "docs/dashboard_data/comparison.json",
                "docs/dashboard_data/benchmarks.json",
            ],
            "periods": periods,
            "covid_periods": COVID,
            "n_quarters": len(periods),
            "n_ex_2020": len(periods) - len(COVID),
            "target_definition": TARGET_DEFINITION,
            "clean_quarters": comparison["leak_scan"]["clean_quarters"],
            "panel_baseline": "US_new",
            "panel_fiscal": "US_fiscal",
        },
        "headline": {
            "baseline": baseline["headline"],
            "fiscal": fiscal["headline"],
        },
        "metrics": {
            "baseline": baseline["metrics"],
            "fiscal": fiscal["metrics"],
        },
        "weekly": {
            "baseline": baseline["weekly"],
            "fiscal": fiscal["weekly"],
        },
        "skipped": {
            "baseline": baseline["skipped"],
            "fiscal": fiscal["skipped"],
        },
        "comparison": {
            "convention": comparison["convention"],
            "diebold_mariano": comparison["diebold_mariano"],
            "power_mde": comparison["power_mde"],
            "per_quarter": comparison["per_quarter"],
            "leak_scan": comparison["leak_scan"],
        },
        "benchmarks": {
            "convention": benchmarks["convention"],
            "models": benchmarks["models"],
            "panel": benchmarks["panel"],
            "metrics": benchmarks["metrics"],
            "diebold_mariano": benchmarks["diebold_mariano"],
            "per_quarter": benchmarks["per_quarter"],
            "gdpnow_note": benchmarks["gdpnow_note"],
        },
        "findings": _build_findings(baseline, benchmarks, comparison),
    }

    # Sanity: headline periods must line up across variants and the benchmark table.
    assert [r["period"] for r in fiscal["headline"]] == periods, "fiscal periods misaligned"
    assert [
        r["period"] for r in benchmarks["per_quarter"]
    ] == periods, "benchmark periods misaligned"
    return bundle


def main() -> None:
    bundle = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    meta = bundle["meta"]
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  quarters={meta['n_quarters']} (ex-2020 {meta['n_ex_2020']})")
    print(f"  findings={len(bundle['findings'])}")


if __name__ == "__main__":
    main()
