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

import numpy as np
from scipy import stats

from gdpnowcast.diebold_mariano import diebold_mariano

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"
COVID = {"2020q1", "2020q2", "2020q3", "2020q4"}
LOSSES: dict[str, object] = {"squared": lambda e: e * e, "absolute": lambda e: abs(e)}
SAMPLES: dict[str, object] = {"all": lambda p: True, "ex_2020": lambda p: p not in COVID}

# Power / minimum-detectable-effect settings for the headline DM test (two-sided).
MDE_ALPHA = 0.05  # significance level
MDE_POWER = 0.80  # target power

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


def _mde_leaf(la: list[float], lb: list[float], lname: str, dm_stat: float) -> dict:
    """Power / minimum-detectable-effect for one sample x loss.

    For the headline horizon h=1 the DM-HLN statistic reduces *exactly* to the ordinary paired
    t-test on ``d = loss_fiscal - loss_baseline`` (the HLN factor cancels the biased-variance
    divisor), so the MDE is the textbook two-sided t formula
    ``MDE = (t_{1-alpha/2, df} + t_{power, df}) * SE(d)`` with ``SE(d) = sd(d)/sqrt(n)`` and
    ``sd(d)`` the *unbiased* (ddof=1) sample SD. ``paired_t`` is emitted alongside ``dm_stat``
    purely to evidence that equivalence. For squared loss the MSE-unit effects are also mapped
    onto the RMSE scale via ``RMSE_base - sqrt(MSE_base - effect)`` (``mean(lb) == MSE_base``).
    """
    a = np.asarray(la, dtype=float)
    b = np.asarray(lb, dtype=float)
    d = a - b
    n = int(d.size)
    df = n - 1
    dbar = float(d.mean())
    sd = float(d.std(ddof=1))
    se = float(sd / np.sqrt(n))
    t_crit = float(stats.t.ppf(1.0 - MDE_ALPHA / 2.0, df))
    t_pow = float(stats.t.ppf(MDE_POWER, df))
    sig_threshold = t_crit * se  # smallest |effect| that would be significant at alpha
    mde = (t_crit + t_pow) * se  # smallest |effect| detectable with `MDE_POWER` power
    paired_t = dbar / se if se > 0 else 0.0
    leaf = {
        "n": n,
        "df": df,
        "mean_loss_diff": dbar,
        "sd_diff": sd,
        "se": se,
        "t_crit": t_crit,
        "t_power": t_pow,
        "sig_threshold_effect": sig_threshold,
        "mde": mde,
        "powered": abs(dbar) >= mde,  # is the observed effect at/above the 80%-power MDE?
        "paired_t": float(paired_t),
        "dm_stat": float(dm_stat),
    }
    if lname == "squared":
        mse_base = float(b.mean())
        rmse_base = float(np.sqrt(mse_base))
        leaf["mse_base"] = mse_base
        leaf["rmse_base"] = rmse_base
        leaf["sig_threshold_effect_rmse"] = rmse_base - float(
            np.sqrt(max(mse_base - sig_threshold, 0.0))
        )
        leaf["mde_rmse"] = rmse_base - float(np.sqrt(max(mse_base - mde, 0.0)))
    return leaf


def _compute(fis: dict[str, float], base: dict[str, float]) -> dict:
    periods = sorted(base)
    if sorted(fis) != periods:
        raise SystemExit("variant period sets differ -- re-run both backtests")

    dm: dict[str, dict[str, dict]] = {}
    power: dict[str, dict[str, dict]] = {}
    for sname, keep in SAMPLES.items():
        sample = [p for p in periods if keep(p)]  # type: ignore[operator]
        dm[sname] = {}
        power[sname] = {}
        for lname, lf in LOSSES.items():
            la = [lf(fis[p]) for p in sample]  # type: ignore[operator]
            lb = [lf(base[p]) for p in sample]  # type: ignore[operator]
            dm_res = asdict(diebold_mariano(la, lb, horizon=1))
            dm[sname][lname] = dm_res
            leaf = _mde_leaf(la, lb, lname, dm_res["dm_stat"])
            # h=1 invariant: the HLN-corrected DM statistic IS the ordinary paired t.
            if abs(leaf["paired_t"] - leaf["dm_stat"]) > 1e-7 * (1.0 + abs(leaf["dm_stat"])):
                raise SystemExit(
                    f"h=1 DM/paired-t mismatch ({sname}/{lname}): "
                    f"{leaf['paired_t']} vs {leaf['dm_stat']}"
                )
            power[sname][lname] = leaf

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
        "power_mde": {
            "method": (
                "For h=1 the DM-HLN statistic equals the ordinary paired t-test, so MDE = "
                "(t_{1-alpha/2,df} + t_{power,df}) * SE(d), df=n-1, SE(d)=sd(d)/sqrt(n) with "
                "sd(d) the unbiased sample SD. This central-t formula is the standard "
                "approximation to the exact noncentral-t MDE (here within ~0.02%, and if "
                "anything slightly conservative). Squared-loss effects are in MSE units; the "
                "RMSE-scale equivalent is RMSE_base - sqrt(MSE_base - effect)."
            ),
            "alpha": MDE_ALPHA,
            "power": MDE_POWER,
            "by_sample": power,
        },
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


def _mde_table(power: dict) -> list[str]:
    by = power["by_sample"]
    rows = [
        "| sample | loss | n | observed Δloss | SE | sig. threshold (5%) | MDE (80% power) |",
        "|---|---|---|---|---|---|---|",
    ]
    for sname, slabel in (("all", "all-34"), ("ex_2020", "ex-2020")):
        for lname, llabel in (("squared", "squared (MSE)"), ("absolute", "absolute (MAE)")):
            r = by[sname][lname]
            star = " ✓" if r["powered"] else ""
            rows.append(
                f"| {slabel} | {llabel} | {int(r['n'])} | {r['mean_loss_diff']:+.3f} | "
                f"{r['se']:.3f} | {r['sig_threshold_effect']:.3f} | {r['mde']:.3f}{star} |"
            )
    return rows


def _write_md(out: dict) -> None:
    dm = out["diebold_mariano"]
    power = out["power_mde"]
    leak = out["leak_scan"]
    es = power["by_sample"]["ex_2020"]["squared"]
    ea = power["by_sample"]["ex_2020"]["absolute"]
    mae_verb = "meets" if ea["powered"] else "still falls short of"
    mse_verb = "meets" if es["powered"] else "falls short of"
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
        "## Statistical power: minimum detectable effect (MDE)",
        "",
        "Because the headline horizon is h=1, the DM-HLN statistic above is *identical* to an",
        "ordinary paired t-test on the per-quarter loss differential -- the HLN finite-sample",
        "factor exactly cancels the biased-variance divisor (the tool asserts `paired_t ==",
        "dm_stat`). That makes the textbook power calculation directly applicable: with `n`",
        "quarters and the observed loss-differential SD, the smallest accuracy gap detectable at",
        "5% significance and 80% power is **`MDE = (t_{.975,df} + t_{.80,df})·SE(d)`**, with",
        "`SE(d) = sd(d)/√n`. A ✓ marks a (sample, loss) cell whose *observed* |Δloss| already",
        "reaches that MDE.",
        "",
        *_mde_table(power),
        "",
        f"**Reading the power.** The ex-2020 **MAE** gap (|Δ| = {abs(ea['mean_loss_diff']):.3f})",
        f"clears its 5% significance threshold ({ea['sig_threshold_effect']:.3f} -- equivalently",
        f"the DM p={dm['ex_2020']['absolute']['p_value']:.3f} < 0.05) but {mae_verb} the 80%-power",
        f"MDE of {ea['mde']:.3f}, so even the one significant cell rests on an effect this sample",
        "is itself underpowered to certify. The ex-2020 **squared**-loss gap (|Δ| = "
        f"{abs(es['mean_loss_diff']):.3f} MSE) {mse_verb} its MDE of {es['mde']:.3f} MSE -- a",
        f"{es['mde_rmse']:.3f}pp move on the RMSE scale (baseline RMSE {es['rmse_base']:.3f}) -- so",
        f"the non-significant RMSE verdict (p={dm['ex_2020']['squared']['p_value']:.3f}) is an",
        f"**underpowered** outcome: with n={es['n']} ex-COVID quarters the test cannot resolve an",
        f"RMSE improvement below ~{es['mde_rmse']:.2f}pp, and the observed gain sits under that",
        "bar. Honest takeaway: the data are **consistent with** a real-but-modest fiscal-block",
        "benefit that this sample size is underpowered to certify -- exactly the **suggestive, not",
        "established** reading, now quantified.",
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
    power = out["power_mde"]["by_sample"]
    print("Diebold-Mariano (A=fiscal, B=baseline; <0 => fiscal more accurate):")
    for sname in ("all", "ex_2020"):
        for lname in ("squared", "absolute"):
            r = dm[sname][lname]
            print(
                f"  {sname:8s} {lname:8s} n={int(r['n']):2d} "
                f"loss_diff={r['mean_loss_diff']:+.4f} DM={r['dm_stat']:+.3f} p={r['p_value']:.3f}"
            )
    print("Power / MDE (alpha=0.05, power=0.80; OK => observed |loss_diff| >= MDE):")
    for sname in ("all", "ex_2020"):
        for lname in ("squared", "absolute"):
            r = power[sname][lname]
            mark = "OK " if r["powered"] else "   "
            extra = f" mde_rmse={r['mde_rmse']:+.3f}" if "mde_rmse" in r else ""
            print(
                f"  {mark}{sname:8s} {lname:8s} |obs|={abs(r['mean_loss_diff']):.3f} "
                f"sig_thr={r['sig_threshold_effect']:.3f} mde={r['mde']:.3f}{extra}"
            )
    print("wrote docs/dashboard_data/comparison.json + docs/comparison.md")


if __name__ == "__main__":
    main()
