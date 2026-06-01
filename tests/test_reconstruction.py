import pandas as pd

from gdpnowcast.data.fred import asof_series, reconstruct_asof


def _history() -> pd.DataFrame:
    # obs 2020-01-01 first published 2020-02-15 (=100), revised 2020-05-15 (=110)
    # obs 2020-02-01 first published 2020-03-15 (=200)
    return pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2020-02-15", "2020-05-15", "2020-03-15"]),
            "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01"]),
            "value": [100.0, 110.0, 200.0],
        }
    )


def test_asof_takes_latest_realtime_not_after_d() -> None:
    s = reconstruct_asof(_history(), pd.Timestamp("2020-04-01"))
    # the 2020-05-15 revision is in the future as of 2020-04-01 -> excluded
    assert s.loc[pd.Timestamp("2020-01-01")] == 100.0
    assert s.loc[pd.Timestamp("2020-02-01")] == 200.0


def test_asof_sees_revision_once_published() -> None:
    s = reconstruct_asof(_history(), pd.Timestamp("2020-06-01"))
    assert s.loc[pd.Timestamp("2020-01-01")] == 110.0


def test_asof_excludes_observations_after_d() -> None:
    # nothing observed after the vintage date can appear
    s = reconstruct_asof(_history(), pd.Timestamp("2020-01-20"))
    assert s.empty  # first publication (2020-02-15) is after 2020-01-20


def test_quarterly_shift_lands_on_last_month_of_quarter() -> None:
    hist = pd.DataFrame(
        {
            "realtime_start": pd.to_datetime(["2020-04-30"]),
            "date": pd.to_datetime(["2020-01-01"]),  # Q1, quarter-start stamp
            "value": [5.0],
        }
    )
    s = asof_series(hist, pd.Timestamp("2020-06-01").date(), frequency="q")
    assert pd.Timestamp("2020-03-01") in s.index  # Jan + 2 months = Mar
    assert pd.Timestamp("2020-01-01") not in s.index
