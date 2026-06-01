"""Load the FRBNY-style model spec (Spec_US_*.xlsx) into typed records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATHS = {
    "baseline": REPO_ROOT / "Spec_US_new.xlsx",
    "fiscal": REPO_ROOT / "Spec_US_fiscal.xlsx",
}


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    name: str
    frequency: str  # "m" or "q"
    transform: str  # lin / chg / ch1 / pch / pc1 / pca / log
    model: int
    category: str


def load_spec(path: Path) -> list[SeriesSpec]:
    df = pd.read_excel(path, sheet_name="spec")
    return [
        SeriesSpec(
            series_id=str(r["SeriesID"]).strip(),
            name=str(r["SeriesName"]).strip(),
            frequency=str(r["Frequency"]).strip().lower(),
            transform=str(r["Transformation"]).strip(),
            model=int(r["Model"]),
            category=str(r["Category"]).strip(),
        )
        for _, r in df.iterrows()
    ]
