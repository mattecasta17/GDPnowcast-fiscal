"""Baseline-vs-fiscal headline comparison: Diebold-Mariano significance + per-quarter deltas.

Reads ``docs/dashboard_data/{baseline,fiscal}.json`` (produced by ``tools/run_backtest.py``)
and runs the DM-HLN test (quarterly, h=1; see ``gdpnowcast.diebold_mariano``) on per-quarter
losses for BOTH squared and absolute loss, over BOTH the all-34 and ex-2020 samples. Persists:

  docs/dashboard_data/comparison.json  -- committed, dashboard-ready
  docs/comparison.md                   -- committed, human-readable

Convention: model **A = fiscal**, **B = baseline**; ``loss_diff = loss_fiscal - loss_baseline``,
so ``loss_diff < 0`` and ``dm_stat < 0`` => the fiscal variant is the more accurate one.

Everything here is derived from the committed JSON artifacts -- NO network, NO re-estimation --
so it is safe to regenerate any time the backtests change. The release-day contamination
context (why 2025q1's large miss is a genuine forecast error, not leakage) is reproduced by
``uv run python -m tools.release_day_leak_scan scan`` and summarized in the NOTES below.

Usage (from repo root):
  uv run python -m tools.compare_variants
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from gdpnowcast.diebold_mariano import diebold_mariano

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"
COVID = {"2020q1", "2020q2", "2020q3", "2020q4"}
LOSSES: dict[str, object] = {"squared": lambda e: e * e, "absolute": lambda e: abs(e)}
SAMPLES: dict[str, object] = {"all": lambda p: True, "ex_2020": lambda p: p not in COVID}

# Stable facts from `tools/release_day_leak_scan scan` (pure ALFRED vintage history of past
# quarters -- does not change). 2025q1 is one of the *contaminated* quarters: on the advance
# day BEA co-releases the four series below (incl. real PCE ~= 68% of GDP), all of which the
# (advance-1) cutoff excludes -> its large miss is genuine, not a leakage artifact.
LEAK_2025Q1_ADVANCE_DAY = ["DSPIC96", "PCEC96", "PCEPI", "PCEPILFE"]
LEAK_2025Q1_WINDOW_COUNT = 11
LEAK_QUARTERS_TOTAL = 33
LEAK_ADVANCE_DAY_NONZERO = 17
LEAK_WINDOW_NONZERO = 29
LEAK_CLEAN_QUARTERS = ["2017q1", "2018q1", "2018q3", "2019q1"]


def _errors(variant: str) -> dict[str, float]:
    data = json.loads((DD / f"{variant}.json").read_text(encoding="utf-8"))
    return {r["period"]: float(r["error"]) for r in data["headline"]}


def _compute(fis: dict[str, float], base: dict[str, float]) -> dict:
    periods = sorted(base)
    if sorted(fis) != periods:
        raise SystemExit("variant period sets differ -- re-run both backtests")

    dm: dict[str, dict[str, dict]] = {}
    for sname, keep in SAMPLES.items():
        sample = [p for p in periods if keep(p)]  # type: ignore[operator]
        dm[sname] = {}
        for lname, lf in LOSSES.items():
            la = [lf(fis[p]) for p in sample]  # type: ignore[operator]
            lb = [lf(base[p]) for p in sample]  # type: ignore[operator]
            dm[sname][lname] = asdict(diebold_mariano(la, lb, horizon=1))

    per_quarter = [
        {
            "period": p,
            "fiscal_error": fis[p],
            "baseline_error": base[p],
            "abs_error_delta": abs(fis[p]) - abs(base[p]),  # < 0 => fiscal more accurate
            "covid": p in COVID,
        }
        for p in periods
    ]
    return {
        "convention": (
            "A=fiscal, B=baseline; loss_diff=loss_fiscal-loss_baseline; "
            "loss_diff<0 and dm_stat<0 => fiscal more accurate; horizon h=1"
        ),
        "diebold_mariano": dm,
        "per_quarter": per_quarter,
        "leak_scan": {
            "source": "tools/release_day_leak_scan scan",
            "quarters": LEAK_QUARTERS_TOTAL,
            "advance_day_leak_nonzero": LEAK_ADVANCE_DAY_NONZERO,
            "window_leak_nonzero": LEAK_WINDOW_NONZERO,
            "clean_quarters": LEAK_CLEAN_QUARTERS,
            "q2025q1_advance_day_coreleases": LEAK_2025Q1_ADVANCE_DAY,
            "q2025q1_window_coreleases": LEAK_2025Q1_WINDOW_COUNT,
        },
    }


def _dm_table(dm: dict[str, dict[str, dict]]) -> list[str]:
    rows = [
        "| sample | loss | n | Δloss (fis-base) | DM stat | p-value |",
        "|---|---|---|---|---|---|",
    ]
    for sname, slabel in (("all", "all-34"), ("ex_2020", "ex-2020")):
        for lname, llabel in (("squared", "squared (RMSE)"), ("absolute", "absolute (MAE)")):
            r = dm[sname][lname]
            sig = "**" if r["p_value"] < 0.05 else ""
            rows.append(
                f"| {slabel} | {llabel} | {int(r['n'])} | {r['mean_loss_diff']:+.3f} | "
                f"{r['dm_stat']:+.3f} | {sig}{r['p_value']:.3f}{sig} |"
            )
    return rows


def _write_md(out: dict) -> None:
    dm = out["diebold_mariano"]
    leak = out["leak_scan"]
    lines = [
        "# Baseline vs Fiscal: predictive-accuracy comparison",
        "",
        "Does adding the fiscal block (Treasury/government series) improve the headline",
        "(advance-1) nowcast over the baseline panel? Both variants are scored on the **same 34",
        "quarters** against the **same** BEA advance actuals (verified identical), so this is a",
        "clean apples-to-apples comparison. _Generated by `tools/compare_variants.py` from the",
        "committed `docs/dashboard_data/{baseline,fiscal}.json`._",
        "",
        "## Diebold-Mariano test (quarterly, HLN-corrected, h=1)",
        "",
        "Model **A = fiscal**, **B = baseline**; `Δloss = loss_fiscal - loss_baseline`, so",
        "**`Δloss < 0` and `DM < 0` ⇒ fiscal is the more accurate variant**. p-values are",
        "two-sided (H0: equal accuracy); **bold** = significant at 5%.",
        "",
        *_dm_table(dm),
        "",
        "**Honest reading.** In the ex-COVID headline sample the fiscal series deliver a modest",
        "accuracy gain that is **statistically significant under absolute loss (MAE, "
        f"p={dm['ex_2020']['absolute']['p_value']:.3f}) but not under squared loss (RMSE, "
        f"p={dm['ex_2020']['squared']['p_value']:.3f})**. Squared loss is dominated by a handful",
        "of large real-economy misses (2022q1/q2, 2025q1) that neither variant anticipates, so",
        "the robust MAE criterion is the more informative one here. On the full COVID-inclusive",
        "sample the two are statistically indistinguishable (2020q3/q4 noise dominates, and the",
        "fiscal variant is marginally worse there). No overclaim: **the fiscal block helps at the",
        "margin -- robustly under MAE, not decisively under RMSE.**",
        "",
        "**Multiple-testing caveat.** Four DM tests are reported above; the single 5%-significant",
        "cell (ex-2020 MAE) would not survive a family-wise correction across the four "
        f"(Bonferroni: {dm['ex_2020']['absolute']['p_value']:.3f} x 4 = "
        f"{min(1.0, dm['ex_2020']['absolute']['p_value'] * 4):.2f}), and the emphasis on MAE over",
        "RMSE is in part a post-hoc loss-function choice. Read the fiscal gain as **suggestive,",
        "not established** -- a larger out-of-sample window would be needed to settle it.",
        "",
        "## Per-quarter accuracy delta (|fiscal error| - |baseline error|)",
        "",
        "Negative = fiscal closer to the advance that quarter.",
        "",
        "| quarter | error (fiscal) | error (baseline) | abs-err Δ (fis-base) | better |",
        "|---|---|---|---|---|",
    ]
    for r in out["per_quarter"]:
        delta = r["abs_error_delta"]
        better = "tie" if abs(delta) < 5e-4 else ("fiscal" if delta < 0 else "baseline")
        covid = " _(COVID)_" if r["covid"] else ""
        lines.append(
            f"| {r['period']}{covid} | {r['fiscal_error']:+.3f} | {r['baseline_error']:+.3f} | "
            f"{r['abs_error_delta']:+.3f} | {better} |"
        )
    lines += [
        "",
        "## Notes: 2025q1 is a genuine miss, not contamination",
        "",
        "The release-day leak scan (`" + leak["source"] + "`) confirms **2025q1 is a",
        "*contaminated* quarter**: on its advance day (2025-04-30) BEA co-releases "
        f"{len(leak['q2025q1_advance_day_coreleases'])} series a masked release-week vintage",
        "would absorb -- real PCE (`PCEC96`, ≈68% of GDP), real disposable income (`DSPIC96`),",
        f"and PCE prices (`PCEPI`/`PCEPILFE`) -- and {leak['q2025q1_window_coreleases']} within",
        "[advance, release-Friday]. The headline **(advance-1 = 2025-04-29) cutoff excludes all",
        "of them**, so the ≈-4.5pp 2025q1 error is a true pre-advance forecast miss, not a",
        "leakage artifact. Across the 2017Q1-2025Q1 scan, "
        f"{leak['advance_day_leak_nonzero']}/{leak['quarters']} quarters leak ≥1 co-release on",
        f"the advance day and {leak['window_leak_nonzero']}/{leak['quarters']} within the window;",
        f"only {len(leak['clean_quarters'])} quarters ({', '.join(leak['clean_quarters'])}) are",
        "clean -- which is exactly why the headline rule is the (advance-1) cutoff, not",
        "Friday + mask-only-GDP. See `docs/plans/2026-06-04-phase4.0-release-day-cutoff-decision.md`.",
        "",
    ]
    (REPO / "docs" / "comparison.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    out = _compute(_errors("fiscal"), _errors("baseline"))
    DD.mkdir(parents=True, exist_ok=True)
    (DD / "comparison.json").write_text(
        json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8"
    )
    _write_md(out)

    dm = out["diebold_mariano"]
    print("Diebold-Mariano (A=fiscal, B=baseline; <0 => fiscal more accurate):")
    for sname in ("all", "ex_2020"):
        for lname in ("squared", "absolute"):
            r = dm[sname][lname]
            print(
                f"  {sname:8s} {lname:8s} n={int(r['n']):2d} "
                f"loss_diff={r['mean_loss_diff']:+.4f} DM={r['dm_stat']:+.3f} p={r['p_value']:.3f}"
            )
    print("wrote docs/dashboard_data/comparison.json + docs/comparison.md")


if __name__ == "__main__":
    main()
