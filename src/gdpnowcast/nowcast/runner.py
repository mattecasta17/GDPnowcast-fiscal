"""Parameterised pseudo-real-time backtest loop (replaces the 18 nowcast_* scripts).

run_quarter re-estimates the prev/curr DFM parameters from their data vintages
(v1 cached opaque pickles at broken absolute paths), then walks the quarter's
weekly vintages, calling update_nowcast on each contiguous (old, new) pair and
collecting y_old/y_new + the news impacts.

Skip handling: v1's nowcast_2017.py wraps every pair in a blanket
``except Exception: continue``. Two real, verified causes make a pair raise (see
the note in the loop) and v1 silently drops them. We reproduce the DROP (so the
output matches v1's CSV) but narrow the catch to the two verified exception types
rather than v1's blanket ``Exception`` -- an unexpected error (missing file, a
porting regression) should surface, not be swallowed. The skipped vintages are
recorded on ``df.attrs["skipped"]`` instead of v1's silent print.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..dfm import dfm
from ..dfm_spec import load_dfm_spec
from ..news import nowcast_point, update_nowcast
from ..transform import load_vintage
from .config import QuarterCfg

_REPO = Path(__file__).resolve().parents[3]
_SAMPLE_START = pd.Timestamp("2000-01-01")  # match v1 production params (sample_start=2000)


def _vfile(subdir: str, v: str) -> str:
    return str(_REPO / "data" / subdir / f"{v}.xlsx")


def run_quarter(
    cfg: QuarterCfg,
    data_subdir: str,
    spec_file: str,
    series: str = "GDPC1",
    mask_target: bool = False,
) -> pd.DataFrame:
    spec = load_dfm_spec(spec_file)
    res_prev = dfm(
        load_vintage(_vfile(data_subdir, cfg.prev_vintage), spec, _SAMPLE_START)[0], spec, 1e-4
    )
    res_curr = dfm(
        load_vintage(_vfile(data_subdir, cfg.curr_vintage), spec, _SAMPLE_START)[0], spec, 1e-4
    )
    switch = pd.Timestamp(cfg.switch_date)

    rows: list[dict] = []
    skipped: list[str] = []
    for i in range(1, len(cfg.vintages)):
        v_old, v_new = cfg.vintages[i - 1], cfg.vintages[i]
        res_use = res_prev if pd.Timestamp(v_new) < switch else res_curr
        try:
            x_old, _, _ = load_vintage(_vfile(data_subdir, v_old), spec)  # news step: FULL sample
            x_new, time, _ = load_vintage(_vfile(data_subdir, v_new), spec)
            out = update_nowcast(
                x_old,
                x_new,
                time,
                spec,
                res_use,
                series,
                cfg.period,
                v_old,
                v_new,
                mask_target=mask_target,
            )
        except (TypeError, ValueError):
            # v1-parity skip. Two verified causes (running the shimmed v1 stack):
            #   * no-news week  -> News_DFM returns actual/forecast=None -> None-None TypeError
            #   * GDP-release week -> target observed -> NO-FORECAST branch shape bug -> ValueError
            # Both drop the pair. (Graceful handling of each is a Phase-4 candidate.)
            skipped.append(v_new)
            continue

        y_new = float(out["y_new"][0])
        rows.append(
            {
                "vintage": v_new,
                "y_old": float(out["y_old"][0]),
                "y_new": y_new,
                "error": cfg.gdp_actual - y_new,
                "impact_revisions": float(out["impact_revisions"][0]),
                "impact_releases": float(np.nansum(out["impact_releases"])),
            }
        )

    df = pd.DataFrame(rows)
    df.attrs["skipped"] = skipped

    # Headline nowcast: the as-of (advance_date - 1 day) PRE-ADVANCE forecast (Phase
    # 4.0 gate decision) -- the tightest cutoff that provably excludes the BEA GDP
    # advance AND its same-day co-releases. Computed standalone via nowcast_point (NOT
    # update_nowcast) so the weekly loop and its goldens are untouched; the target GDP
    # cell is NaN in this vintage by construction -> a genuine forecast. Full-sample
    # load like the news step. res_head reuses the switch boundary (advance-1 is always
    # within its own quarter, so == res_curr here, but kept general for later quarters).
    #
    # The headline is a v2-panel (US_new/US_fiscal) concept; its (advance-1) cutoff
    # vintage is built by tools/build_headline_vintages. On panels that do not carry it
    # -- notably the US_new_v1 golden-parity fixture, which holds only the v1 Friday
    # manifest, not the Thursday cutoff -- expose headline=None rather than hard-failing
    # the weekly backtest (keeps the golden/masked tests, which run on US_new_v1, green).
    adv_minus_1 = (pd.Timestamp(cfg.advance_date) - pd.Timedelta(days=1)).date().isoformat()
    headline_file = Path(_vfile(data_subdir, adv_minus_1))
    if headline_file.exists():
        res_head = res_prev if pd.Timestamp(adv_minus_1) < switch else res_curr
        xh, timeh, _ = load_vintage(str(headline_file), spec)
        y_head = nowcast_point(xh, timeh, spec, res_head, series, cfg.period)
        df.attrs["headline"] = {
            "vintage": adv_minus_1,
            "y_new": y_head,
            "error": cfg.gdp_actual - y_head,
        }
    else:
        df.attrs["headline"] = None
    return df
