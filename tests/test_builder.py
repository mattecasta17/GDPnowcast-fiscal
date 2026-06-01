from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from gdpnowcast.data.builder import build_vintage, monthly_index, write_vintage
from gdpnowcast.data.spec import SeriesSpec


def _specs() -> list[SeriesSpec]:
    return [
        SeriesSpec("PAYEMS", "Payroll", "m", "chg", 1, "Labor"),
        SeriesSpec("GDPC1", "GDP", "q", "pca", 1, "National Accounts"),
    ]


def _histories() -> dict[str, pd.DataFrame]:
    payems = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2019-02-01", "2019-03-01"]),
            "date": pd.to_datetime(["2019-01-01", "2019-02-01"]),
            "value": [150000.0, 150500.0],
        }
    )
    gdp = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2019-01-30"]),
            "date": pd.to_datetime(["2018-10-01"]),  # Q4 2018, quarter-start stamp
            "value": [19000.0],
        }
    )
    return {"PAYEMS": payems, "GDPC1": gdp}


def test_monthly_index_runs_1985_to_vintage_month() -> None:
    idx = monthly_index(date(2020, 7, 25))
    assert idx[0] == pd.Timestamp("1985-01-01")
    assert idx[-1] == pd.Timestamp("2020-07-01")
    assert (idx.day == 1).all()


def test_build_vintage_format() -> None:
    df = build_vintage(_histories(), _specs(), date(2019, 3, 15))
    assert list(df.columns) == ["Date", "PAYEMS", "GDPC1"]
    assert df["Date"].iloc[0] == pd.Timestamp("1985-01-01")
    assert df["Date"].iloc[-1] == pd.Timestamp("2019-03-01")
    # monthly value present, future months NaN (no leakage / no ffill)
    row_jan = df.loc[df["Date"] == pd.Timestamp("2019-01-01"), "PAYEMS"].iloc[0]
    assert row_jan == 150000.0
    assert np.isnan(df.loc[df["Date"] == pd.Timestamp("2019-03-01"), "PAYEMS"].iloc[0])
    # quarterly GDP stamped on Dec (Q4 last month), not Oct
    assert df.loc[df["Date"] == pd.Timestamp("2018-12-01"), "GDPC1"].iloc[0] == 19000.0
    assert np.isnan(df.loc[df["Date"] == pd.Timestamp("2018-10-01"), "GDPC1"].iloc[0])


def test_write_vintage_roundtrip(tmp_path: Path) -> None:
    df = build_vintage(_histories(), _specs(), date(2019, 3, 15))
    path = write_vintage(df, tmp_path, date(2019, 3, 15))
    assert path.name == "2019-03-15.xlsx"
    back = pd.read_excel(path)
    assert "Date" in back.columns
    assert {"PAYEMS", "GDPC1"} <= set(back.columns)
