"""Blocks-aware DFM spec loader — typed port of Functions/load_spec.py.
Separate from data/spec.py (the fetcher spec): the DFM needs the block-loading
matrix, the Model==1 filter, and frequency-sorted numpy arrays."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

_FREQ_ORDER = ["d", "w", "m", "q", "sa", "a"]
_FIELDS = ["SeriesID", "SeriesName", "Frequency", "Units", "Transformation", "Category"]
_UNITS_T = {
    "lin": "Levels (No Transformation)",
    "chg": "Change (Difference)",
    "ch1": "Year over Year Change (Difference)",
    "pch": "Percent Change",
    "pc1": "Year over Year Percent Change",
    "pca": "Percent Change (Annual Rate)",
    "cch": "Continuously Compounded Rate of Change",
    "cca": "Continuously Compounded Annual Rate of Change",
    "log": "Natural Log",
}


@dataclass(frozen=True)
class DfmSpec:
    series_id: np.ndarray
    series_name: np.ndarray
    frequency: np.ndarray
    units: np.ndarray
    transformation: np.ndarray
    category: np.ndarray
    units_transformed: np.ndarray
    blocks: np.ndarray
    block_names: list[str]

    # v1-compatible aliases so the verbatim-ported dfm.py / News_DFM bodies work unedited.
    @property
    def Blocks(self) -> np.ndarray:  # noqa: N802
        return self.blocks

    @property
    def SeriesID(self) -> np.ndarray:  # noqa: N802
        return self.series_id

    @property
    def SeriesName(self) -> np.ndarray:  # noqa: N802
        return self.series_name

    @property
    def Frequency(self) -> np.ndarray:  # noqa: N802
        return self.frequency

    @property
    def Units(self) -> np.ndarray:  # noqa: N802
        return self.units

    @property
    def Category(self) -> np.ndarray:  # noqa: N802
        return self.category

    @property
    def Transformation(self) -> np.ndarray:  # noqa: N802
        return self.transformation

    @property
    def UnitsTransformed(self) -> np.ndarray:  # noqa: N802
        return self.units_transformed

    @property
    def BlockNames(self) -> list[str]:  # noqa: N802
        return self.block_names


def load_dfm_spec(filename: str | Path) -> DfmSpec:
    raw = pd.read_excel(filename)
    raw.columns = [c.replace(" ", "") for c in raw.columns]
    raw = raw[raw["Model"] == 1].reset_index(drop=True)

    order: list[int] = []
    for freq in _FREQ_ORDER:
        order += list(raw[raw.Frequency == freq].index)
    raw = raw.loc[order, :]

    for field in _FIELDS:
        if field not in raw.columns:
            raise ValueError(f"{field}: column missing from model specification.")

    block_cols = list(raw.columns[raw.columns.str.contains("Block", case=False)])
    blocks = raw[block_cols].copy()
    blocks[blocks.isna()] = 0
    if not (blocks.iloc[:, 0] == 1).all():
        raise ValueError("All variables must load on the global block.")

    transformation = raw["Transformation"].to_numpy(copy=True)
    return DfmSpec(
        series_id=raw["SeriesID"].to_numpy(copy=True),
        series_name=raw["SeriesName"].to_numpy(copy=True),
        frequency=raw["Frequency"].to_numpy(copy=True),
        units=raw["Units"].to_numpy(copy=True),
        transformation=transformation,
        category=raw["Category"].to_numpy(copy=True),
        units_transformed=np.array([_UNITS_T[t] for t in transformation]),
        blocks=blocks.to_numpy(copy=True),
        block_names=[re.sub("Block[0-9]+-", "", c) for c in block_cols],
    )
