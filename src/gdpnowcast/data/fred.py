"""ALFRED point-in-time fetch + local as-of reconstruction.

Forward-looking-bias guardrail (Matteo's standing concern, napkin Domain #4):
reconstruct_asof keeps, for each observation date, only the latest value whose
realtime_start <= D, and never returns an observation dated after D. No ffill,
no interpolation, no backfill - missing cells stay missing."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_START = pd.Timestamp("1985-01-01")


def get_fred() -> Fred:
    # override=True: .env is the single source of truth; a stale OS-level
    # FRED_API_KEY (e.g. Windows User env) must not shadow it. See napkin Tooling #3.
    load_dotenv(REPO_ROOT / ".env", override=True)
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY is not set. Copy .env.example to .env and add your key.")
    return Fred(api_key=key)


def fetch_release_history(fred: Fred, series_id: str) -> pd.DataFrame:
    """Full ALFRED release history: tidy [realtime_start, date, value] (float)."""
    raw = fred.get_series_all_releases(series_id)
    df = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(raw["realtime_start"]),
            "date": pd.to_datetime(raw["date"]),
            "value": pd.to_numeric(raw["value"], errors="coerce"),
        }
    )
    return df.dropna(subset=["value"]).reset_index(drop=True)


def reconstruct_asof(history: pd.DataFrame, as_of: pd.Timestamp) -> pd.Series:
    """Series as known at as_of: latest value per obs date with realtime_start <= as_of,
    restricted to observations dated <= as_of. Quarter-start stamping is preserved
    (no shift here - that is applied in asof_series)."""
    known = history[history["realtime_start"] <= as_of]
    if known.empty:
        return pd.Series(dtype=float)
    s = known.sort_values("realtime_start").groupby("date")["value"].last().sort_index()
    return s[s.index <= as_of]


def asof_series(history: pd.DataFrame, as_of: date, frequency: str) -> pd.Series:
    """reconstruct_asof + quarterly stamping. Quarterly series (frequency='q') are
    shifted +2 months so a quarter-start observation lands on the last month of the
    quarter (Mar/Jun/Sep/Dec), matching the v1 ingest convention (napkin Domain #1)."""
    s = reconstruct_asof(history, pd.Timestamp(as_of))
    if frequency == "q" and not s.empty:
        s = s.copy()
        s.index = s.index + pd.DateOffset(months=2)
    return s
