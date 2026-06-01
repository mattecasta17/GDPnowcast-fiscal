import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

from gdpnowcast.data.fred import fetch_release_history, get_fred, reconstruct_asof

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=True)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("FRED_API_KEY"),
        reason="needs FRED_API_KEY (.env) - skipped in offline CI",
    ),
]


@pytest.mark.parametrize("series_id", ["PPIFIS", "GCEC1", "PAYEMS"])
@pytest.mark.parametrize("as_of", ["2018-07-06", "2020-04-01", "2023-01-03"])
def test_reconstruction_matches_direct_pointintime(series_id: str, as_of: str) -> None:
    fred = get_fred()
    history = fetch_release_history(fred, series_id)
    recon = reconstruct_asof(history, pd.Timestamp(as_of)).dropna()
    direct = fred.get_series(series_id, realtime_start=as_of, realtime_end=as_of).dropna()
    direct.index = pd.to_datetime(direct.index)
    # same observation coverage and identical values (point-in-time, no leakage)
    assert list(recon.index) == list(direct.index)
    pd.testing.assert_series_equal(
        recon, direct, check_names=False, check_freq=False, rtol=0, atol=0
    )


@pytest.mark.parametrize("as_of", ["2017-01-03", "2021-04-01"])
def test_no_observation_after_vintage(as_of: str) -> None:
    fred = get_fred()
    history = fetch_release_history(fred, "PAYEMS")
    recon = reconstruct_asof(history, pd.Timestamp(as_of))
    assert recon.index.max() <= pd.Timestamp(as_of)


def test_fetch_smoke_two_vintages(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from gdpnowcast.cli import app

    result = CliRunner().invoke(
        app,
        ["fetch", "--variant", "fiscal", "--data-dir", str(tmp_path), "--limit", "2"],
    )
    assert result.exit_code == 0, result.output
    out = sorted((tmp_path / "US_fiscal").glob("*.xlsx"))
    assert len(out) == 2
    back = pd.read_excel(out[0])
    assert "Date" in back.columns
    assert len([c for c in back.columns if c != "Date"]) == 35
