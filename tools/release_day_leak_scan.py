"""Phase 4.0 gate evidence: release-day cutoff / same-day-contamination analysis.

Records (reproducibly) the analysis behind the 2026-06-04 gate decision to score
the headline backtest against an *as-of (advance - 1 day)* pre-advance forecast,
NOT a fixed-Thursday calendar and NOT Friday + mask-only-GDP. See
``docs/plans/2026-06-04-phase4.0-release-day-cutoff-decision.md``.

Three phases:
  * ``scan`` -- THE headline evidence. For every quarter 2017Q1..latest it finds the
    GDP advance date and counts non-GDP series released in [advance, release-Friday]
    (the data a masked release-week vintage holds that a pre-advance forecast does
    not). Result: 29/33 quarters leak BEA co-releases (real PCE, real income, PCE
    prices, durable goods); 17/33 even on the advance day itself. Pure ALFRED-history
    scan, no EM, no vintage build.
  * ``build`` -- builds Thursday (Friday-1) 2017Q1 vintages into ``data/US_new_thu``
    and prints the mechanism diagnostic (advance absent Thu, present Fri).
  * ``run`` -- heavy EM comparison of Friday+mask vs Thursday arms for 2017Q1
    (all three coincide at y_new=2.246138 -- 2017Q1 is one of only 4 clean quarters).

Dev tool, NOT wired into the CLI. ``build``/``run`` write the gitignored, disposable
``data/US_new_thu``; ``scan`` writes nothing. Needs a working FRED_API_KEY in ``.env``.

Usage (from repo root):
    uv run python -m tools.release_day_leak_scan scan    # the gate evidence
    uv run python -m tools.release_day_leak_scan build   # 2017Q1 Thu data + diagnostic
    uv run python -m tools.release_day_leak_scan run      # heavy: 2017Q1 EM comparison
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from gdpnowcast.data.builder import build_vintage, write_vintage
from gdpnowcast.data.fred import fetch_release_history, get_fred
from gdpnowcast.data.spec import SPEC_PATHS, load_spec
from gdpnowcast.data.vintages import load_manifest
from gdpnowcast.nowcast.config import CONFIG_2017Q1
from gdpnowcast.nowcast.runner import run_quarter

REPO = Path(__file__).resolve().parents[1]
THU_SUBDIR = "US_new_thu"
SPEC_FILE = "Spec_US_new.xlsx"  # baseline, matches the masked 2017Q1 test
TARGET = "GDPC1"
Q1_ROW = pd.Timestamp("2017-03-01")  # 2017Q1 obs, stamped to last month of quarter


def _thursday(iso_friday: str) -> str:
    """Friday weekly vintage -> the prior Thursday (one day earlier)."""
    return (date.fromisoformat(iso_friday) - timedelta(days=1)).isoformat()


def _thu_vintages() -> tuple[str, ...]:
    return tuple(_thursday(v) for v in CONFIG_2017Q1.vintages)


def _needed_dates() -> list[str]:
    # Thursday weeklies + the two param re-estimation vintages (kept UNCHANGED so
    # prev/curr DFM params are identical to the Friday arm -> isolates the day effect).
    return sorted(set(_thu_vintages()) | {CONFIG_2017Q1.prev_vintage, CONFIG_2017Q1.curr_vintage})


def _gdp_at_q1(xlsx: Path) -> float:
    df = pd.read_excel(xlsx)
    df["Date"] = pd.to_datetime(df["Date"])
    hit = df.loc[df["Date"] == Q1_ROW, TARGET]
    return float("nan") if hit.empty else float(hit.iloc[0])


def build() -> None:
    specs = load_spec(SPEC_PATHS["baseline"])
    out_dir = REPO / "data" / THU_SUBDIR
    needed = _needed_dates()
    missing = [d for d in needed if not (out_dir / f"{d}.xlsx").exists()]

    if missing:
        fred = get_fred()
        print(f"fetching {len(specs)} release histories from ALFRED ...")
        histories = {sp.series_id: fetch_release_history(fred, sp.series_id) for sp in specs}
        for d in missing:
            as_of = date.fromisoformat(d)
            write_vintage(build_vintage(histories, specs, as_of), out_dir, as_of)
        print(f"built {len(missing)} vintage(s) -> {out_dir}")
    else:
        print(f"all {len(needed)} vintages already in {out_dir}")

    # Decisive mechanism check: on the release week, the BEA Q1 advance must be
    # ABSENT as-of Thursday and PRESENT as-of Friday (same fresh ALFRED source).
    thu = REPO / "data" / THU_SUBDIR / f"{_thursday('2017-04-28')}.xlsx"
    fri = REPO / "data" / "US_new" / "2017-04-28.xlsx"
    print("\n=== mechanism check: GDPC1 2017Q1 (row 2017-03-01) ===")
    print(f"  Thursday 2017-04-27 : {_gdp_at_q1(thu)!r:>10}  (expect NaN -> genuine forecast)")
    print(f"  Friday   2017-04-28 : {_gdp_at_q1(fri)!r:>10}  (expect a number -> advance observed)")


def _report(label: str, df: pd.DataFrame, release_vintage: str, actual: float) -> None:
    print(f"\n-- {label} --")
    print(f"   rows={len(df)}  skipped={df.attrs.get('skipped')}")
    if release_vintage in list(df["vintage"]):
        row = df[df["vintage"] == release_vintage].iloc[0]
        y = float(row["y_new"])
        print(
            f"   release-week {release_vintage}: y_new={y:.6f}  error({actual}-y)={actual - y:+.4f}"
        )
    else:
        print(f"   release-week {release_vintage}: DROPPED (not in output)")


def run() -> None:
    actual = CONFIG_2017Q1.gdp_actual
    thu_cfg = replace(CONFIG_2017Q1, vintages=_thu_vintages())
    thu_release = _thursday("2017-04-28")

    print("\n=== 2017Q1 release-week comparison (all on fresh v2 ALFRED panel) ===")

    df_fri = run_quarter(CONFIG_2017Q1, "US_new", SPEC_FILE, TARGET, mask_target=True)
    _report("Friday + mask (data/US_new)", df_fri, "2017-04-28", actual)

    df_thu = run_quarter(thu_cfg, THU_SUBDIR, SPEC_FILE, TARGET, mask_target=False)
    _report("Thursday, NO mask (data/US_new_thu)", df_thu, thu_release, actual)

    df_thu_m = run_quarter(thu_cfg, THU_SUBDIR, SPEC_FILE, TARGET, mask_target=True)
    _report("Thursday + mask (data/US_new_thu)", df_thu_m, thu_release, actual)


def scan() -> None:
    """Quantify Matteo's same-day concern across ALL quarters, pure history scan.

    For each quarter Q (from 2017Q1): advance = first realtime_start of Q's GDP;
    release-Fri = first manifest vintage >= advance. The masked release vintage
    includes every non-GDP series with realtime_start in [advance, release-Fri]
    that an as-of-(advance-1) pre-advance forecast would NOT -> that window IS the
    contamination Matteo flagged. No EM, no Thursday fetch; reuses cached histories.
    """
    specs = load_spec(SPEC_PATHS["baseline"])
    fred = get_fred()
    print(f"fetching {len(specs)} release histories from ALFRED ...")
    hist = {sp.series_id: fetch_release_history(fred, sp.series_id) for sp in specs}

    manifest = [pd.Timestamp(d) for d in sorted(load_manifest("baseline"))]
    gdp = hist[TARGET]
    advance_by_obs = gdp.groupby("date")["realtime_start"].min()
    advance_by_obs = advance_by_obs[advance_by_obs.index >= pd.Timestamp("2017-01-01")]

    # per non-GDP series: set of normalized release dates
    rt = {
        sid: set(pd.to_datetime(df["realtime_start"]).dt.normalize())
        for sid, df in hist.items()
        if sid != TARGET
    }

    print(
        f"\n{'quarter':9} {'advance':12} {'rel-Fri':11} {'#advday':>7} {'#window':>7}"
        "  advance-day co-releases (intrinsic to masking-only-GDP)"
    )
    rows = []
    for obs_date, adv_ts in advance_by_obs.items():
        advance = pd.Timestamp(adv_ts).normalize()
        rel = next((d for d in manifest if d >= advance), None)
        if rel is None:
            continue
        window = set(pd.date_range(advance, rel, freq="D"))
        adv_hits = sorted(sid for sid, days in rt.items() if advance in days)
        win_hits = sorted(sid for sid, days in rt.items() if days & window)
        q = f"{obs_date.year}Q{(obs_date.month - 1) // 3 + 1}"
        rows.append((q, len(adv_hits), len(win_hits)))
        print(
            f"{q:9} {advance.date()!s:12} {rel.date()!s:11} {len(adv_hits):>7} {len(win_hits):>7}  {adv_hits}"
        )

    nz_adv = [r for r in rows if r[1] > 0]
    nz_win = [r for r in rows if r[2] > 0]
    print(
        f"\nquarters: {len(rows)}  |  advance-day leak >0: {len(nz_adv)} "
        f"(max {max((r[1] for r in rows), default=0)})  |  full-window leak >0: {len(nz_win)} "
        f"(max {max((r[2] for r in rows), default=0)})"
    )


def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("build", "all"):
        build()
    if phase in ("run", "all"):
        run()
    if phase == "scan":
        scan()
    if phase not in ("build", "run", "all", "scan"):
        raise SystemExit(f"unknown phase {phase!r}; use build | run | all | scan")


if __name__ == "__main__":
    main()
