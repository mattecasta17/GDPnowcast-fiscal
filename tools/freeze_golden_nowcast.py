"""Phase 3a: freeze the v1 2017q1 nowcast golden by running the (A0-shimmed) v1
update_nowcast2 on the v1 data backup. Params estimated with sample_start=2000
(matching production); the news step uses FULL-sample data (matching
nowcast_2017.py, which calls load_data without a sample arg).

Usage:  uv run python -m tools.freeze_golden_nowcast
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

from Functions.dfm import dfm
from Functions.load_data import load_data
from Functions.load_spec import load_spec
from Functions.update_Nowcast2 import update_nowcast2

REPO = Path(__file__).resolve().parents[1]
THRESHOLD = 1e-4
SAMPLE_START = date(2000, 1, 1).toordinal() + 366
SERIES, PERIOD = "GDPC1", "2017q1"
SWITCH = np.datetime64("2017-01-01")
VINTAGES = [
    "2016-12-02",
    "2016-12-09",
    "2016-12-16",
    "2016-12-23",
    "2016-12-30",
    "2017-01-06",
    "2017-01-13",
    "2017-01-20",
    "2017-01-27",
    "2017-02-03",
    "2017-02-10",
    "2017-02-17",
    "2017-02-24",
    "2017-03-03",
    "2017-03-10",
    "2017-03-17",
    "2017-03-24",
    "2017-03-31",
    "2017-04-07",
    "2017-04-14",
    "2017-04-21",
    "2017-04-28",
]


def vfile(v: str) -> str:
    return str(REPO / "data" / "US_new_v1" / f"{v}.xlsx")


def main() -> None:
    spec = load_spec("Spec_US_new.xlsx")
    xp, _, _ = load_data(vfile("2016-10-03"), spec, SAMPLE_START)  # prev params
    res_prev = dfm(xp, spec, THRESHOLD)
    xc, _, _ = load_data(vfile("2017-01-03"), spec, SAMPLE_START)  # curr params
    res_curr = dfm(xc, spec, THRESHOLD)

    # v1's nowcast_2017.py wraps each update_nowcast2 call in try/except and does
    # `print("Skipping ..."); continue` on ANY error. This silently drops vintage
    # pairs via TWO distinct, version-independent failure modes (both verified by
    # running the A0-shimmed v1 stack on these vintages):
    #   (A) NO-NEWS WEEKS (2016-12-30, 2017-02-24): no indicator was released that
    #       week, so News_DFM hits FORECAST SUBCASE (A) and returns actual/forecast
    #       = None; update_nowcast2 then does `None - None` -> TypeError
    #       (update_Nowcast2.py:68).
    #   (B) GDP-RELEASE WEEK (2017-04-28): the Q1 advance GDP print lands, so the
    #       target is observed and News_DFM takes the NO-FORECAST branch -- which
    #       has a latent shape bug: t_fcst is a 1-elem array, so
    #       `y_old[0,i] = X_sm[t_fcst, v_news[i]]` assigns a (1,)-array into a
    #       scalar slot -> ValueError (update_Nowcast.py:170), NOT `None - None`.
    # The golden records whichever exception each pair actually raised, so it must
    # replicate both: record only the pairs v1 actually produced + the skips.
    rows = []
    skipped = []
    for i in range(1, len(VINTAGES)):
        v_old, v_new = VINTAGES[i - 1], VINTAGES[i]
        res_use = res_prev if np.datetime64(v_new) < SWITCH else res_curr
        try:
            x_old, _, _ = load_data(vfile(v_old), spec)  # news step: FULL sample
            x_new, time, _ = load_data(vfile(v_new), spec)
            r = update_nowcast2(
                x_old, x_new, time, spec, res_use, SERIES, PERIOD, v_old, v_new, display=False
            )
            rows.append(
                {
                    "vintage_old": v_old,
                    "vintage": v_new,
                    "y_old": float(r["y_old"][0]),
                    "y_new": float(r["y_new"][0]),
                    "impact_revisions": float(r["impact_revisions"][0]),
                    "impact_releases": float(np.nansum(r["impact_releases"])),
                }
            )
        except Exception as e:  # replicate v1's blanket skip-on-error (nowcast_2017.py)
            print(f"Skipping {v_new}: {type(e).__name__}: {e}")
            skipped.append(
                {"vintage_old": v_old, "vintage": v_new, "reason": f"{type(e).__name__}"}
            )
    out = REPO / "tests" / "golden" / "dfm_legacy_nowcast.json"
    out.write_text(
        json.dumps(
            {
                "period": PERIOD,
                "series": SERIES,
                "sample_start_iso": "2000-01-01",
                "rows": rows,
                "skipped": skipped,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out} ({len(rows)} rows, {len(skipped)} skipped)")


if __name__ == "__main__":
    main()
