"""Generate configs/quarters.json -- the 34-quarter (2017q1-2025q2) Phase-4 backtest registry.

Combines the offline AST extraction (tools.extract_quarter_configs.build_registry, which
reads the v1 nowcast_YYYY.py calendars/params) with ALFRED advance dates (first
``realtime_start`` of each quarter-start GDPC1 observation) and writes the committed
configs/quarters.json. The vintage lists ARE configuration, like configs/vintages_*.csv.

The baseline scripts are canonical; fiscal-vs-baseline calendar diffs are reported (1 known
v1 typo: 2017q3 fiscal has a Saturday vintage). The runner is variant-agnostic
(data_subdir/spec_file), so one registry serves both variants.

Needs a working FRED_API_KEY in .env (get_fred -> load_dotenv(override=True)). ALFRED is hit
only here at generation time; config.py reads the JSON offline.

Usage (from repo root):
    uv run python -m tools.gen_quarter_configs
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from gdpnowcast.data.fred import fetch_release_history, get_fred
from tools.extract_quarter_configs import build_registry

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "configs" / "quarters.json"
TARGET = "GDPC1"


def _quarter_start(period: str) -> pd.Timestamp:
    """'YYYYqQ' -> FRED-native quarter-start obs date (2017q1 -> 2017-01-01)."""
    y_str, q_str = period.split("q")
    return pd.Timestamp(int(y_str), 3 * (int(q_str) - 1) + 1, 1)


def main() -> None:
    registry, fiscal_diffs = build_registry()
    if fiscal_diffs:
        print(
            f"NOTE: {len(fiscal_diffs)} fiscal calendar diff(s), baseline canonical: "
            f"{sorted(fiscal_diffs)}"
        )

    fred = get_fred()
    print(f"fetching {TARGET} release history from ALFRED ...")
    gdp = fetch_release_history(fred, TARGET)

    for period, entry in registry.items():
        obs = _quarter_start(period)
        adv = gdp.loc[gdp["date"] == obs, "realtime_start"].min()
        if pd.isna(adv):
            raise SystemExit(f"{period}: no GDPC1 observation dated {obs.date()} in ALFRED")
        entry["advance_date"] = pd.Timestamp(adv).normalize().date().isoformat()

    OUT.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(registry)} quarters -> {OUT}")


if __name__ == "__main__":
    main()
