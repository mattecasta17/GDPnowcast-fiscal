"""Vintage .xlsx -> (X transformed, Time, Z raw) for the DFM.
Typed port of Functions/load_data.py: MATLAB +366 removed (Time is a real
DatetimeIndex), np.in1d->np.isin, unraised ValueErrors fixed, dead lin:x*2
lambda dropped. Numerically identical to v1 on X (tests/test_transform.py)."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .dfm_spec import DfmSpec

_FREQ_STEP = {"m": 1, "q": 3}


def _read(datafile: str) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    if os.path.splitext(datafile)[1] not in (".xlsx", ".xls"):
        raise ValueError("File is not an Excel file")
    dat = pd.read_excel(datafile)
    mnem = np.array([c for c in dat.columns if c != "Date"])
    return dat[mnem].to_numpy(copy=True), pd.DatetimeIndex(pd.to_datetime(dat["Date"])), mnem


def _sort(z: np.ndarray, mnem: np.ndarray, spec: DfmSpec) -> np.ndarray:
    keep = np.isin(mnem, spec.series_id)
    mnem, z = mnem[keep], z[:, keep]
    perm = np.array([np.where(mnem == s)[0][0] for s in spec.series_id])
    return z[:, perm]


def _transform(z: np.ndarray, spec: DfmSpec) -> np.ndarray:
    t, n = z.shape
    x = np.full((t, n), np.nan)
    for i in range(n):
        f = spec.transformation[i]
        step = _FREQ_STEP[spec.frequency[i]]
        t1 = step - 1
        years = step / 12
        col = z[:, i].copy()
        if f == "lin":
            x[:, i] = col
        elif f == "chg":
            x[t1::step, i] = np.append(np.nan, col[t1 + step :: step] - col[t1 : -1 - t1 : step])
        elif f == "ch1":
            x[12 + t1 :: step, i] = col[12 + t1 :: step] - col[t1:-12:step]
        elif f == "pch":
            x[t1::step, i] = (
                np.append(np.nan, col[t1 + step :: step] / col[t1 : -1 - t1 : step]) - 1
            ) * 100
        elif f == "pc1":
            x[12 + t1 :: step, i] = ((col[12 + t1 :: step] / col[t1:-12:step]) - 1) * 100
        elif f == "pca":
            x[t1::step, i] = (
                np.append(np.nan, col[t1 + step :: step] / col[t1:-step:step]) ** (1 / years) - 1
            ) * 100
        elif f == "log":
            x[:, i] = np.log(col)
        else:
            raise ValueError(f"{f}: transformation is unknown")
    return x


def load_vintage(
    datafile: str, spec: DfmSpec, sample_start: pd.Timestamp | None = None
) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    z, time, mnem = _read(datafile)
    z = _sort(z, mnem, spec)
    x = _transform(z, spec)
    x, time, z = x[3:, :], time[3:], z[3:, :]  # drop first quarter
    if sample_start is not None:
        keep = time >= sample_start
        x, time, z = x[keep, :], time[keep], z[keep, :]
    return x, time, z
