"""Vintage-date manifests. The manifest is the authoritative vintage list,
extracted from the real v1 files (tools/make_vintage_manifest.py). The Fridays
helper exists only so a test can prove the manifest drops nothing (the historical
fridays_between bug omitted the 33 quarter-start re-estimation vintages)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATHS = {
    "baseline": REPO_ROOT / "configs" / "vintages_baseline.csv",
    "fiscal": REPO_ROOT / "configs" / "vintages_fiscal.csv",
}


def load_manifest(variant: str) -> list[date]:
    df = pd.read_csv(MANIFEST_PATHS[variant], dtype={"vintage": str})
    return sorted(date.fromisoformat(s) for s in df["vintage"])


def fridays_between(start: date, end: date) -> list[date]:
    return [d.date() for d in pd.date_range(start=start, end=end, freq="W-FRI")]
