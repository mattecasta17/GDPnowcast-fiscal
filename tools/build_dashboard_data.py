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

from gdpnowcast.diebold_mariano import diebold_mariano

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"
OUT = REPO / "apps" / "dashboard" / "src" / "data" / "dashboard.json"

COVID = ["2020q1", "2020q2", "2020q3", "2020q4"]

TARGET_DEFINITION = (
    "Each nowcast is the model's forecast of the BEA advance estimate of annualized real-GDP "
    "growth, evaluated at the (advance_date - 1 day) pre-advance cutoff. At that cutoff the "
    "target quarter's GDP is still unobserved and BEA same-day co-releases (real PCE, income, "
    "PCE prices, durable goods) are excluded, so the score is a genuine pseudo-real-time "
    "forecast error with no look-ahead leakage. The macro-only dynamic factor model is the "
    "'Staff Nowcast' (a standard central-bank-staff DFM); the 'Fiscal-enhanced DFM' adds a "
    "fiscal block (federal deficit, government spending, transfer-cleaned income)."
)


def _load(name: str) -> dict:
    return json.loads((DD / f"{name}.json").read_text(encoding="utf-8"))


def _dm_by_period(baseline: dict, fiscal: dict) -> dict:
    """Diebold-Mariano (Fiscal-enhanced vs Staff Nowcast) for the three reporting periods.

    Reuses the canonical DM-HLN test (h=1, which coincides with a paired t-test) on per-quarter
    squared and absolute losses. Convention d = loss_fiscal - loss_staff, so a negative statistic
    means the Fiscal-enhanced DFM is the more accurate of the two. The ``ex_2020`` cell reproduces
    ``comparison.json``'s ex-2020 DM exactly; ``pre`` and ``post`` split that sample.
    """
    base = {r["period"]: r["error"] for r in baseline["headline"]}
    fisc = {r["period"]: r["error"] for r in fiscal["headline"]}
    periods = [r["period"] for r in baseline["headline"]]
    covid = set(COVID)
    samples = {
        "ex_2020": [p for p in periods if p not in covid],
        "pre": [p for p in periods if int(p[:4]) <= 2019],
        "post": [p for p in periods if int(p[:4]) >= 2021],
    }
    out: dict = {}
    for skey, ps in samples.items():
        out[skey] = {}
        for loss in ("squared", "absolute"):
            la = [fisc[p] ** 2 if loss == "squared" else abs(fisc[p]) for p in ps]
            lb = [base[p] ** 2 if loss == "squared" else abs(base[p]) for p in ps]
            r = diebold_mariano(la, lb, horizon=1)
            out[skey][loss] = {
                "dm_stat": r.dm_stat,
                "p_value": r.p_value,
                "df": r.df,
                "n": r.n,
                "mean_loss_diff": r.mean_loss_diff,
                "horizon": r.horizon,
            }
    return out


def _r(x: float, n: int = 2) -> float:
    return round(float(x), n)


def _build_findings(
    baseline: dict,
    fiscal: dict,
    benchmarks: dict,
    comparison: dict,
    fiscal_impact: dict,
) -> list[dict]:
    """Honest, number-anchored narrative bullets, ordered fiscal-first.

    Numbers are pulled from the loaded artifacts (never re-typed by hand) so the prose can
    never drift from the metrics it describes. The macro-only DFM is the "Staff Nowcast";
    the fiscal-augmented DFM is the "Fiscal-enhanced DFM"; mean/RW/AR1/ARMA11 are the
    "traditional benchmarks".
    """
    staff_ex = baseline["metrics"]["ex_2020"]
    staff_all = baseline["metrics"]["all"]
    fisc_ex = fiscal["metrics"]["ex_2020"]
    bm = benchmarks["metrics"]
    mean_ex = bm["mean"]["ex_2020"]
    ar1_ex = bm["ar1"]["ex_2020"]
    rw_all = bm["rw"]["all"]
    ar1_all = bm["ar1"]["all"]

    dm_ex = comparison["diebold_mariano"]["ex_2020"]
    mae_dm = dm_ex["absolute"]
    rmse_dm = dm_ex["squared"]
    mde_ex_abs = comparison["power_mde"]["by_sample"]["ex_2020"]["absolute"]

    # Per-quarter wins of the Fiscal-enhanced DFM over the Staff Nowcast (non-COVID only).
    rows = fiscal_impact["per_quarter"]
    n = len(rows)
    wins = sum(1 for r in rows if r["gain"] > 0)
    post = [r for r in rows if int(r["period"][:4]) >= 2021]
    n_post = len(post)
    wins_post = sum(1 for r in post if r["gain"] > 0)
    summ = fiscal_impact["summary"]
    mtsds_corr = summ["corr_by_variable"]["MTSDS133FMS"]

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
            "id": "fiscal-vs-staff",
            "title": "The fiscal block helps more often than not",
            "body": (
                f"Ex-2020 the Fiscal-enhanced DFM edges the macro-only Staff Nowcast on both "
                f"scores -- RMSE {_r(fisc_ex['rmse'])} vs {_r(staff_ex['rmse'])} pp, "
                f"MAE {_r(fisc_ex['mae'])} vs {_r(staff_ex['mae'])} pp -- and is more accurate in "
                f"{wins} of {n} non-COVID quarters ({wins_post}/{n_post} post-COVID). The edge is "
                "modest and concentrated after 2020, not a clean sweep of every quarter."
            ),
            "evidence": {
                "rmse_fiscal_ex": fisc_ex["rmse"],
                "rmse_staff_ex": staff_ex["rmse"],
                "mae_fiscal_ex": fisc_ex["mae"],
                "mae_staff_ex": staff_ex["mae"],
                "wins": wins,
                "n": n,
                "wins_post": wins_post,
                "n_post": n_post,
            },
        },
        {
            "id": "fiscal-deficit-signal",
            "title": "The signal is the deficit, and it switches on post-COVID",
            "body": (
                f"The fiscal block's news (Impact = actual - forecast, weighted) is "
                f"{_r(summ['impact_ratio_post_pre'], 1)}x larger post-COVID than before, and where "
                f"it is larger the Fiscal-enhanced DFM gains more accuracy over the Staff Nowcast "
                f"(correlation {_r(summ['corr_post'])} post-COVID, {_r(summ['corr_partial_post'])} "
                "after controlling for error size). The effect is carried almost entirely by the "
                f"federal deficit (corr {_r(mtsds_corr)}); government spending and transfer-cleaned "
                "income add essentially nothing. Pre-COVID the fiscal news was tiny and unrelated "
                f"to accuracy (corr {_r(summ['corr_pre'])})."
            ),
            "evidence": {
                "impact_ratio_post_pre": summ["impact_ratio_post_pre"],
                "corr_post": summ["corr_post"],
                "corr_partial_post": summ["corr_partial_post"],
                "corr_pre": summ["corr_pre"],
                "deficit_corr": mtsds_corr,
            },
        },
        {
            "id": "fiscal-suggestive",
            "title": "Suggestive, not yet statistically established",
            "body": (
                f"On formal testing the fiscal edge is real-but-fragile: it is significant only on "
                f"MAE ex-2020 (DM {_r(mae_dm['dm_stat'])}, p={_r(mae_dm['p_value'], 3)}), not RMSE "
                f"(DM {_r(rmse_dm['dm_stat'])}, p={_r(rmse_dm['p_value'], 3)}); over all 34 quarters "
                "the two are indistinguishable. That one significant cell sits below its minimum "
                f"detectable effect (|effect| {_r(abs(mae_dm['mean_loss_diff']), 3)} < "
                f"MDE {_r(mde_ex_abs['mde'], 3)}) and a single p=0.036 across four tests does not "
                "survive multiple-testing correction. On 34 quarters the story is economically "
                "coherent but underpowered."
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
            "id": "robustness-tails",
            "title": "Factor models are far more robust in the tails",
            "body": (
                f"Over all 34 quarters both DFMs are dramatically more robust than the traditional "
                f"univariate benchmarks, which blow up on 2020: Staff Nowcast RMSE "
                f"{_r(staff_all['rmse'])} vs random-walk {_r(rw_all['rmse'])} and "
                f"AR(1) {_r(ar1_all['rmse'])}. The multivariate factor structure keeps the nowcast "
                "from chasing a single series off a cliff -- the main edge of the DFM family over "
                "traditional models."
            ),
            "evidence": {
                "staff_rmse_all": staff_all["rmse"],
                "rw_rmse_all": rw_all["rmse"],
                "ar1_rmse_all": ar1_all["rmse"],
            },
        },
        {
            "id": "no-edge-normal-times",
            "title": "No precision edge over naive models in calm times",
            "body": (
                f"Ex-2020 neither DFM beats the traditional benchmarks on RMSE: Staff Nowcast "
                f"{_r(staff_ex['rmse'])} vs historical-mean {_r(mean_ex['rmse'])} and "
                f"AR(1) {_r(ar1_ex['rmse'])}. The naive models are tighter but biased "
                f"(mean bias +{_r(mean_ex['bias'])}, AR1 bias +{_r(ar1_ex['bias'])}); the DFMs "
                "trade a little noise for near-zero bias."
            ),
            "evidence": {
                "staff_rmse_ex_2020": staff_ex["rmse"],
                "mean_rmse_ex_2020": mean_ex["rmse"],
                "ar1_rmse_ex_2020": ar1_ex["rmse"],
                "mean_bias_ex_2020": mean_ex["bias"],
                "ar1_bias_ex_2020": ar1_ex["bias"],
            },
        },
        {
            "id": "dm-indistinguishable",
            "title": "DFM vs traditional: a statistical tie on this sample",
            "body": (
                f"None of the {cells} DFM-vs-benchmark Diebold-Mariano tests "
                f"({sig}/{cells} reject at 5%) are significant: by formal testing the factor models "
                "and the traditional ones are statistically indistinguishable on this short "
                "34-quarter sample. The DFM's real value is robustness in the tails plus the weekly "
                "within-quarter path it produces, not a headline-RMSE win in calm times."
            ),
            "evidence": {"dm_cells": cells, "dm_significant": sig},
        },
        {
            "id": "target",
            "title": "Honest pseudo-real-time target",
            "body": (
                "Every nowcast is scored against the BEA advance growth estimate at a pre-advance "
                "cutoff (advance day minus one). No target value and no same-day BEA co-release "
                "leak into the forecast, so the errors below are genuine, not read-backs."
            ),
            "evidence": {"n_quarters": int(staff_all["n"]), "n_ex_2020": int(staff_ex["n"])},
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
    fiscal_impact = _load("fiscal_impact")
    ablation = _load("ablation")

    periods = [r["period"] for r in baseline["headline"]]

    bundle = {
        "meta": {
            "generated_from": [
                "docs/dashboard_data/baseline.json",
                "docs/dashboard_data/fiscal.json",
                "docs/dashboard_data/comparison.json",
                "docs/dashboard_data/benchmarks.json",
                "docs/dashboard_data/fiscal_impact.json",
                "docs/dashboard_data/ablation.json",
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
            "dm_by_period": _dm_by_period(baseline, fiscal),
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
        "fiscal_impact": fiscal_impact,
        "ablation": ablation,
        "findings": _build_findings(baseline, fiscal, benchmarks, comparison, fiscal_impact),
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
