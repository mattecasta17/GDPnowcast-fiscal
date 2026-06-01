"""Assemble a point-in-time vintage into the v1 Excel format:
a monthly `Date` column (1985-01 .. vintage month) + one column per SeriesID,
quarterly series stamped on the last month of the quarter, missing cells NaN."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .fred import DATA_START, asof_series
from .spec import SeriesSpec


def monthly_index(as_of: date) -> pd.DatetimeIndex:
    end = pd.Timestamp(as_of.year, as_of.month, 1)
    return pd.date_range(DATA_START, end, freq="MS")


def build_vintage(
    histories: dict[str, pd.DataFrame], specs: list[SeriesSpec], as_of: date
) -> pd.DataFrame:
    idx = monthly_index(as_of)
    df = pd.DataFrame(index=idx)
    for sp in specs:
        series = asof_series(histories[sp.series_id], as_of, sp.frequency)
        df[sp.series_id] = series.reindex(idx)  # reindex -> NaN for missing, never ffill
    df.index.name = "Date"
    return df.reset_index()


def write_vintage(df: pd.DataFrame, out_dir: Path, as_of: date) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{as_of.isoformat()}.xlsx"
    df.to_excel(path, index=False)
    return path
