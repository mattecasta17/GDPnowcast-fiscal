"""Sanity checks for the dashboard export layer (tools/build_dashboard_data.py).

Fast + offline: derives only from the committed docs/dashboard_data/*.json artifacts, so it
runs in the default `just ci` lane. Asserts the consolidated bundle is well-formed and that the
copied-through sections stay byte-identical to their sources (the export must never silently
mutate a number).
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.build_dashboard_data import build

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"


def _src(name: str) -> dict:
    return json.loads((DD / f"{name}.json").read_text(encoding="utf-8"))


def test_bundle_shape() -> None:
    b = build()
    assert set(b) == {
        "meta",
        "headline",
        "metrics",
        "weekly",
        "skipped",
        "comparison",
        "benchmarks",
        "findings",
    }
    meta = b["meta"]
    assert meta["n_quarters"] == len(meta["periods"]) == 34
    assert meta["n_ex_2020"] == 30
    assert meta["periods"][0] == "2017q1"
    # weekly + headline aligned across both variants
    for variant in ("baseline", "fiscal"):
        assert [r["period"] for r in b["headline"][variant]] == meta["periods"]
        assert len(b["weekly"][variant]) == 34


def test_sections_match_source() -> None:
    """Copied-through sections must equal their source artifacts exactly."""
    b = build()
    baseline, fiscal = _src("baseline"), _src("fiscal")
    comparison, benchmarks = _src("comparison"), _src("benchmarks")

    assert b["headline"]["baseline"] == baseline["headline"]
    assert b["headline"]["fiscal"] == fiscal["headline"]
    assert b["metrics"]["baseline"] == baseline["metrics"]
    assert b["benchmarks"]["metrics"] == benchmarks["metrics"]
    assert b["comparison"]["diebold_mariano"] == comparison["diebold_mariano"]
    assert b["comparison"]["power_mde"] == comparison["power_mde"]
    assert b["weekly"]["fiscal"] == fiscal["weekly"]


def test_findings_numbers_track_source() -> None:
    """Generated findings must quote numbers pulled from the artifacts, not stale literals."""
    b = build()
    benchmarks = _src("benchmarks")
    comparison = _src("comparison")
    fid = {f["id"]: f for f in b["findings"]}

    assert set(fid) == {
        "target",
        "headline",
        "no-edge-normal-times",
        "robustness-tails",
        "dm-indistinguishable",
        "fiscal-suggestive",
        "leak-2025q1",
    }
    # honest finding: 0/16 benchmark DM cells significant
    assert fid["dm-indistinguishable"]["evidence"] == {"dm_cells": 16, "dm_significant": 0}
    # DFM ex-2020 RMSE traced straight from benchmarks.json
    assert (
        fid["headline"]["evidence"]["rmse_ex_2020"]
        == benchmarks["metrics"]["dfm"]["ex_2020"]["rmse"]
    )
    # fiscal MAE effect below its MDE (underpowered) -- the "suggestive not established" claim
    ev = fid["fiscal-suggestive"]["evidence"]
    assert ev["mae_p_value"] == comparison["diebold_mariano"]["ex_2020"]["absolute"]["p_value"]
    assert ev["mae_abs_effect"] < ev["mae_mde"]
