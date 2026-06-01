"""ALFRED coverage go/no-go spike for Phase 2 (design doc section 8, open-q #2).

For every series in the fiscal spec (35 = 32 baseline + 3 fiscal), confirm that
the series can be rebuilt point-in-time from ALFRED across the backtest window:

  1. ID resolves on FRED (get_series_info) and we capture its observation_start.
  2. ALFRED has a *vintage history* reaching back to <= the first backtest vintage
     (VINTAGE_START = 2016-12-09) -> we can reconstruct every weekly + quarter-start
     vintage. A series with no vintages, or whose earliest vintage is later than
     VINTAGE_START, cannot be reconstructed before that point.
  3. A point-in-time as-of query at VINTAGE_START returns data (unless the series
     legitimately starts after 2016-12, in which case an empty as-of is expected
     and NOT a failure -- we cross-check against observation_start).

Prints a per-series coverage table and an overall GO / NO-GO verdict. Series that
fail the vintage check need an explicit fallback: ship committed vintages as a
release artifact. NEVER backfill an as-of cell -- that leaks future data.

Run:  uv run python tools/alfred_coverage_spike.py
Needs FRED_API_KEY in .env (or the environment).
"""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

# ---------- settings ----------
REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "Spec_US_fiscal.xlsx"  # superset: 32 baseline + 3 fiscal

VINTAGE_START = date(2016, 12, 9)  # first backtest vintage (v1 VINTAGE_START)
VINTAGE_END = date(2025, 7, 25)  # last backtest vintage (v1 VINTAGE_END)

PAUSE_BETWEEN_CALLS = 0.6
MAX_RETRIES = 6
BACKOFF_START_SEC = 2.0
# ------------------------------


def get_fred() -> Fred:
    # override=True: .env is the single source of truth for this repo. A stale
    # OS-level FRED_API_KEY (e.g. an old key in Windows User env) must NOT shadow it.
    load_dotenv(REPO_ROOT / ".env", override=True)
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is not set. Copy .env.example to .env, fill in your "
            "FRED API key, then re-run."
        )
    return Fred(api_key=api_key)


def _retry(call, label: str):
    """Run a fredapi call with rate-limit backoff. Returns (value, error_str)."""
    wait = BACKOFF_START_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call(), None
        except Exception as exc:
            msg = str(exc)
            transient = (
                any(s in msg for s in ("Too Many Requests", "Exceeded Rate Limit", "timed out"))
                or "connection" in msg.lower()
            )
            if transient and attempt < MAX_RETRIES:
                print(
                    f"    rate-limited on {label} (try {attempt}/{MAX_RETRIES}); wait {wait:.1f}s"
                )
                time.sleep(wait)
                wait *= 2
                continue
            return None, msg
        finally:
            time.sleep(PAUSE_BETWEEN_CALLS)
    return None, "max retries exceeded"


def load_series_spec() -> pd.DataFrame:
    df = pd.read_excel(SPEC_PATH, sheet_name="spec")
    return df[["SeriesID", "SeriesName", "Frequency", "Model", "Transformation", "Category"]].copy()


def probe_series(fred: Fred, series_id: str) -> dict[str, object]:
    out: dict[str, object] = {
        "id": series_id,
        "resolves": False,
        "obs_start": None,
        "n_vintages": None,
        "earliest_vintage": None,
        "covers_2016_12": False,
        "asof_start_nonempty": False,
        "asof_recent_nonempty": False,
        "error": "",
    }

    info, err = _retry(lambda: fred.get_series_info(series_id), f"info:{series_id}")
    if err:
        out["error"] = f"info: {err[:80]}"
        return out
    out["resolves"] = True
    out["obs_start"] = str(info.get("observation_start", ""))

    vds, err = _retry(lambda: fred.get_series_vintage_dates(series_id), f"vintages:{series_id}")
    if err:
        out["error"] = f"vintages: {err[:80]}"
    else:
        dates = sorted(pd.to_datetime(list(vds)))
        out["n_vintages"] = len(dates)
        if dates:
            earliest = dates[0].date()
            out["earliest_vintage"] = earliest.isoformat()
            out["covers_2016_12"] = earliest <= VINTAGE_START

    s0, _err0 = _retry(
        lambda: fred.get_series(
            series_id,
            realtime_start=VINTAGE_START.isoformat(),
            realtime_end=VINTAGE_START.isoformat(),
        ),
        f"asof_start:{series_id}",
    )
    out["asof_start_nonempty"] = bool(s0 is not None and not s0.empty)

    s1, _err1 = _retry(
        lambda: fred.get_series(
            series_id,
            realtime_start=VINTAGE_END.isoformat(),
            realtime_end=VINTAGE_END.isoformat(),
        ),
        f"asof_recent:{series_id}",
    )
    out["asof_recent_nonempty"] = bool(s1 is not None and not s1.empty)

    return out


def verdict(row: dict[str, object]) -> str:
    """GO / WARN / NO-GO for a single series."""
    if not row["resolves"]:
        return "NO-GO"  # ID does not resolve on FRED
    if not row["covers_2016_12"]:
        # No vintages, or earliest vintage later than 2016-12-09.
        return "NO-GO"
    if not row["asof_recent_nonempty"]:
        return "WARN"  # vintages exist but recent as-of empty -> investigate
    return "GO"


def main() -> None:
    fred = get_fred()
    spec = load_series_spec()
    print(f"Spec: {SPEC_PATH.name} -- {len(spec)} series")
    print(f"Backtest window: {VINTAGE_START} .. {VINTAGE_END}\n")

    rows: list[dict[str, object]] = []
    for _, r in spec.iterrows():
        sid = str(r["SeriesID"]).strip()
        print(f"-> {sid} ({r['Frequency']}, model={r['Model']}) ...")
        res = probe_series(fred, sid)
        res["freq"] = r["Frequency"]
        res["model"] = int(r["Model"])
        res["transform"] = r["Transformation"]
        res["v"] = verdict(res)
        rows.append(res)

    # ---- table ----
    hdr = (
        f"\n{'SeriesID':<20} {'fq':<2} {'md':<2} {'resolv':<6} {'obs_start':<11} "
        f"{'#vint':>6} {'earliest':<11} {'>=16-12':<7} {'as-of@end':<9} {'verdict':<6}"
    )
    print(hdr)
    print("-" * len(hdr))
    for x in rows:
        print(
            f"{x['id']!s:<20} {x['freq']!s:<2} {x['model']:<2} "
            f"{'yes' if x['resolves'] else 'NO':<6} {x['obs_start'] or ''!s:<11} "
            f"{x['n_vintages'] if x['n_vintages'] is not None else '?'!s:>6} "
            f"{x['earliest_vintage'] or '-'!s:<11} "
            f"{('yes' if x['covers_2016_12'] else 'NO'):<7} "
            f"{('yes' if x['asof_recent_nonempty'] else 'no'):<9} {x['v']!s:<6}"
        )
        if x["error"]:
            print(f"    ! {x['error']}")

    # ---- summary ----
    go = [x for x in rows if x["v"] == "GO"]
    warn = [x for x in rows if x["v"] == "WARN"]
    nogo = [x for x in rows if x["v"] == "NO-GO"]
    print("\n=== SUMMARY ===")
    print(f"GO: {len(go)}   WARN: {len(warn)}   NO-GO: {len(nogo)}   (of {len(rows)})")
    if warn:
        print("WARN (vintages exist, recent as-of empty -> investigate):")
        for x in warn:
            print(f"  - {x['id']}: {x['error'] or 'recent as-of empty'}")
    if nogo:
        print("NO-GO (no usable vintage history back to 2016-12 -> needs fallback):")
        for x in nogo:
            print(f"  - {x['id']}: earliest={x['earliest_vintage']} {x['error']}")
    overall = "GO" if not nogo else ("CONDITIONAL-GO (fallbacks needed)" if go else "NO-GO")
    print(f"\nOVERALL: {overall}")


if __name__ == "__main__":
    main()
