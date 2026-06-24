"""Build the fiscal-block news-impact artifact for the dashboard.

The thesis's original contribution is that the *fiscal block* — chiefly the federal
deficit (``MTSDS133FMS``) — carries a real-time signal that becomes material post-COVID:
in those quarters the fiscal variables' news (``Impact = (Actual - Forecast) * Weight``)
is several times larger, and where it is larger the Fiscal-enhanced DFM gains more accuracy
over the macro-only Staff Nowcast.

This tool quantifies that from the committed per-variable news workbooks in
``news_Q_fiscal/`` and the headline errors in ``docs/dashboard_data/{baseline,fiscal}.json``,
and writes a small committed artifact:

  docs/dashboard_data/fiscal_impact.json

which ``tools.build_dashboard_data`` folds into the dashboard bundle. Keeping the heavy
xlsx read here (run once, committed) means the bundle build stays pure-JSON and network-free,
consistent with the other artifacts.

Definitions (per non-COVID quarter):
  fiscal_impact  = sum over weekly vintages of |Impact| for the fiscal-block series
  gain           = |error_staff| - |error_fiscal|   (>0 => Fiscal-enhanced more accurate)
  share          = fiscal_impact / sum |Impact| over ALL series that quarter

Pre-COVID = years <= 2019, Post-COVID = years >= 2021, COVID (2020) excluded throughout.

Usage (from repo root):
  uv run python -m tools.build_fiscal_impact
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"
NEWS_DIR = REPO / "news_Q_fiscal"
OUT = DD / "fiscal_impact.json"

COVID = {"2020q1", "2020q2", "2020q3", "2020q4"}

# The three series in US_fiscal but not in US_new. The deficit is the genuine fiscal
# instrument; W875RX1 is transfer-cleaned market income; GCEC1 is quarterly govt spending.
FISCAL_BLOCK = [
    {"id": "MTSDS133FMS", "label": "Federal deficit", "short": "Deficit"},
    {"id": "W875RX1", "label": "Income ex-transfers", "short": "Income ex-tr."},
    {"id": "GCEC1", "label": "Govt spending", "short": "Govt spend"},
]
BLOCK_IDS = [v["id"] for v in FISCAL_BLOCK]


def _load(name: str) -> dict:
    return json.loads((DD / f"{name}.json").read_text(encoding="utf-8"))


def _news_path(period: str) -> Path:
    year, q = period[:4], period[4:]  # "2022q2" -> "2022", "q2"
    return NEWS_DIR / f"news_{year}_{q}_fiscal.xlsx"


def _quarter_impact(period: str) -> dict | None:
    path = _news_path(period)
    if not path.exists():
        return None
    xl = pd.ExcelFile(path)
    per = {v: 0.0 for v in BLOCK_IDS}
    per_signed = {v: 0.0 for v in BLOCK_IDS}
    total_abs = 0.0
    block_abs = 0.0
    block_signed = 0.0
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        df = df.rename(columns={df.columns[0]: "var"}).set_index("var")
        imp = df["Impact"]
        total_abs += float(imp.abs().sum())
        for v in BLOCK_IDS:
            if v in imp.index and pd.notna(imp.loc[v]):
                val = float(imp.loc[v])
                per[v] += abs(val)
                per_signed[v] += val
                block_abs += abs(val)
                block_signed += val
    return {
        "impact": block_abs,
        "signed": block_signed,
        "share": block_abs / total_abs if total_abs else float("nan"),
        "per": per,
        "per_signed": per_signed,
    }


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def _partial(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    """corr(x, y | z) — controls for a confounder z (here, the error scale)."""

    def resid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        design = np.c_[np.ones(len(b)), b]
        beta = np.linalg.lstsq(design, a, rcond=None)[0]
        return a - design @ beta

    return _pearson(resid(x, z), resid(y, z))


def _cc(x: np.ndarray, y: np.ndarray) -> dict:
    """Pearson r + p. (Spearman dropped: on n<=18 the rank test discards the shock-magnitude
    information that is the economic content of the hypothesis; the short-sample fragility is
    disclosed in prose instead.)"""
    r, p = stats.pearsonr(x, y)
    return {"r": _round(float(r), 3), "p": _round(float(p), 3)}


def _fit(x: np.ndarray, y: np.ndarray) -> dict:
    """OLS slope/intercept (np.polyfit deg 1) for drawing the scatter's fitted line."""
    slope, intercept = np.polyfit(x, y, 1)
    return {"slope": _round(float(slope), 4), "intercept": _round(float(intercept), 4)}


def _signed_summary(df: pd.DataFrame, pre: pd.DataFrame, post: pd.DataFrame) -> dict:
    """Signed deficit news vs growth. The featured (non-circular) axis is ``resid`` =
    realized - macro-only Staff Nowcast; ``growth`` = raw realized growth is kept as context.
    fit_post is the OLS line over the post-COVID points."""

    def block(ycol: str) -> dict:
        return {
            "pre": _cc(pre.signed_def.to_numpy(), pre[ycol].to_numpy()),
            "post": _cc(post.signed_def.to_numpy(), post[ycol].to_numpy()),
            "all": _cc(df.signed_def.to_numpy(), df[ycol].to_numpy()),
            "fit_post": _fit(post.signed_def.to_numpy(), post[ycol].to_numpy()),
        }

    # Post-COVID decomposition for the "incremental contribution" panel. staff = realized -
    # resid (the macro-only Staff Nowcast). The point: the deficit signal is near-orthogonal
    # to the (weak) macro nowcast, so its link to the macro residual is genuinely incremental.
    sd_post = post.signed_def.to_numpy()
    gr_post = post.realized.to_numpy()
    rs_post = post.resid.to_numpy()
    staff_post = gr_post - rs_post
    return {
        "mean_deficit_pre": _round(float(pre.signed_def.mean()), 4),
        "mean_deficit_post": _round(float(post.signed_def.mean()), 4),
        "growth": block("realized"),
        "resid": block("resid"),
        "decomposition_post": {
            "deficit_vs_growth": _cc(sd_post, gr_post),
            "macro_vs_growth": _cc(staff_post, gr_post),
            "deficit_vs_macro": _cc(sd_post, staff_post),
            "deficit_vs_resid": _cc(sd_post, rs_post),
        },
    }


def build() -> dict:
    baseline = _load("baseline")
    fiscal = _load("fiscal")
    b_err = {r["period"]: r["abs_error"] for r in baseline["headline"]}
    f_err = {r["period"]: r["abs_error"] for r in fiscal["headline"]}
    # Realized BEA advance growth (the common target) and the macro-only Staff Nowcast
    # headline, for the signed deficit-vs-growth scatter (the non-circular y = realized -
    # staff, plus the raw realized growth as context).
    b_adv = {r["period"]: r["gdp_advance"] for r in baseline["headline"]}
    b_staff = {r["period"]: r["headline_nowcast"] for r in baseline["headline"]}
    periods = [r["period"] for r in baseline["headline"]]

    rows: list[dict] = []
    for p in periods:
        if p in COVID:
            continue
        qi = _quarter_impact(p)
        if qi is None:
            continue
        err_staff = b_err[p]
        gain = err_staff - f_err[p]
        realized = b_adv[p]
        staff = b_staff[p]
        rows.append(
            {
                "period": p,
                "covid": False,
                "impact": _round(qi["impact"], 4),
                "share": _round(qi["share"], 4),
                "gain": _round(gain, 4),
                "err_staff": _round(err_staff, 4),
                "per_variable": {v: _round(qi["per"][v], 4) for v in BLOCK_IDS},
                # Signed deficit news = the GDP-nowcast revision attributable to the federal
                # deficit (signed; >0 => larger deficit pushed the nowcast up). realized = BEA
                # advance growth; staff_nowcast = macro-only headline; resid_vs_staff is the
                # part of growth the macro-only model misses (the non-circular scatter axis).
                "signed_deficit": _round(qi["per_signed"]["MTSDS133FMS"], 4),
                "realized": _round(realized, 4),
                "staff_nowcast": _round(staff, 4),
                "resid_vs_staff": _round(realized - staff, 4),
            }
        )

    df = pd.DataFrame(
        [
            {
                "p": r["period"],
                "year": int(r["period"][:4]),
                "impact": r["impact"],
                "share": r["share"],
                "gain": r["gain"],
                "err": r["err_staff"],
                "signed_def": r["signed_deficit"],
                "realized": r["realized"],
                "resid": r["resid_vs_staff"],
                **{v: r["per_variable"][v] for v in BLOCK_IDS},
            }
            for r in rows
        ]
    )
    pre = df[df.year <= 2019]
    post = df[df.year >= 2021]
    rel_gain = (df.gain / df.err).to_numpy()
    post_rel = (post.gain / post.err).to_numpy()

    summary = {
        "n_all": len(df),
        "n_pre": len(pre),
        "n_post": len(post),
        "mean_impact_pre": _round(float(pre.impact.mean()), 4),
        "mean_impact_post": _round(float(post.impact.mean()), 4),
        "impact_ratio_post_pre": _round(float(post.impact.mean() / pre.impact.mean()), 2),
        "mean_share_pre": _round(float(pre.share.mean()), 4),
        "mean_share_post": _round(float(post.share.mean()), 4),
        "corr_all": _round(_pearson(df.impact.to_numpy(), df.gain.to_numpy()), 3),
        "corr_pre": _round(_pearson(pre.impact.to_numpy(), pre.gain.to_numpy()), 3),
        "corr_post": _round(_pearson(post.impact.to_numpy(), post.gain.to_numpy()), 3),
        "corr_relative_all": _round(_pearson(df.impact.to_numpy(), rel_gain), 3),
        "corr_relative_post": _round(_pearson(post.impact.to_numpy(), post_rel), 3),
        "corr_partial_all": _round(
            _partial(df.impact.to_numpy(), df.gain.to_numpy(), df.err.to_numpy()), 3
        ),
        "corr_partial_post": _round(
            _partial(post.impact.to_numpy(), post.gain.to_numpy(), post.err.to_numpy()), 3
        ),
        "corr_by_variable": {
            v: _round(_pearson(df[v].to_numpy(), df.gain.to_numpy()), 3) for v in BLOCK_IDS
        },
        "signed": _signed_summary(df, pre, post),
    }

    return {
        "convention": (
            "Impact = (Actual - Forecast) * Weight, summed |.| over the weekly vintages of a "
            "quarter for the fiscal-block series. gain = |error_StaffNowcast| - "
            "|error_FiscalEnhanced| (>0 => fiscal block helps). signed_deficit = signed Impact of "
            "MTSDS133FMS (the GDP-nowcast revision from deficit news; >0 => bigger deficit pushed "
            "the nowcast up). resid_vs_staff = realized advance growth - macro-only Staff Nowcast "
            "(the non-circular axis for the signed scatter). summary.signed reports Pearson r+p of "
            "signed_deficit vs {growth=realized, resid=realized-staff}, pre/post/all, with the "
            "post-COVID OLS fit and a decomposition_post block (deficit/macro/residual cross-corrs). "
            "Pre-COVID <=2019, Post-COVID >=2021, 2020 excluded."
        ),
        "fiscal_block": FISCAL_BLOCK,
        "per_quarter": rows,
        "summary": summary,
    }


def _round(x: float, n: int) -> float:
    return round(float(x), n)


def main() -> None:
    bundle = build()
    OUT.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    s = bundle["summary"]
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  quarters={s['n_all']} (pre {s['n_pre']}, post {s['n_post']})")
    print(f"  fiscal impact post/pre = {s['impact_ratio_post_pre']}x")
    print(
        f"  corr(impact,gain) all={s['corr_all']} post={s['corr_post']} partial_post={s['corr_partial_post']}"
    )
    sg = s["signed"]
    print(
        f"  signed deficit mean pre={sg['mean_deficit_pre']} post={sg['mean_deficit_post']}; "
        f"corr(signed,growth) post r={sg['growth']['post']['r']} (p={sg['growth']['post']['p']}); "
        f"corr(signed,resid) post r={sg['resid']['post']['r']} (p={sg['resid']['post']['p']})"
    )


if __name__ == "__main__":
    main()
