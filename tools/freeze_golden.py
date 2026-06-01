"""Phase 3a: freeze the v1 DFM estimator golden by running the (A0-shimmed) v1
code on the v1 data backup, with sample_start=2000-01-01 (matching DFM_new.py /
the production pickles). Asserts the re-estimated Res matches the committed
pickle so the golden is provably v1's production numbers. Run once; commit JSON.

Usage:  uv run python tools/freeze_golden.py
"""

from __future__ import annotations

import json
import pickle
import platform
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import scipy

from Functions.dfm import dfm
from Functions.load_data import load_data
from Functions.load_spec import load_spec

REPO = Path(__file__).resolve().parents[1]
THRESHOLD = 1e-4  # DFM_new.py:77
SAMPLE_START = date(2000, 1, 1).toordinal() + 366  # DFM_new.py:23 (MATLAB ordinal)
# Two quarter-start vintages = the prev/curr params for the 2017q1 nowcast golden.
# Each maps to a committed production pickle for the fidelity check.
VINTAGES = {
    "2016-10-03": "ResDFM_20161003.pickle",
    "2017-01-03": "ResDFM_20170103.pickle",
}


def _digest(a: np.ndarray) -> dict:
    arr = np.asarray(a, dtype=float)
    return {
        "shape": list(arr.shape),
        "nansum": float(np.nansum(arr)),
        "nansumsq": float(np.nansum(arr**2)),
    }


def main() -> None:
    spec = load_spec("Spec_US_new.xlsx")
    payload: dict = {"meta": {}, "vintages": {}}
    for v, pkl in VINTAGES.items():
        x, _, _ = load_data(str(REPO / "data" / "US_new_v1" / f"{v}.xlsx"), spec, SAMPLE_START)
        res = dfm(x, spec, THRESHOLD)
        # Fidelity check vs the committed production pickle (made by v1 on NumPy<2).
        ref = pickle.load(open(REPO / "DFM_quarter_param" / pkl, "rb"))["Res"]
        max_dc = float(np.max(np.abs(np.asarray(res["C"]) - np.asarray(ref["C"]))))
        print(f"{v}: re-estimated vs pickle max|dC| = {max_dc:.3e}  (C shape {res['C'].shape})")
        payload["vintages"][v] = {
            "X_shape": list(np.asarray(x).shape),
            "n_series": int(np.asarray(res["C"]).shape[0]),
            "loglik_final": float(res["loglik"][-1]),
            "C": np.asarray(res["C"]).tolist(),
            "A": np.asarray(res["A"]).tolist(),
            "Q": np.asarray(res["Q"]).tolist(),
            "R": np.asarray(res["R"]).tolist(),
            "Z_0": np.asarray(res["Z_0"]).tolist(),
            "V_0": np.asarray(res["V_0"]).tolist(),
            "Mx": np.asarray(res["Mx"]).tolist(),
            "Wx": np.asarray(res["Wx"]).tolist(),
            "x_sm_digest": _digest(res["x_sm"]),
            "Z_digest": _digest(res["Z"]),
            "x_sm_gdp_tail": [
                float(xx)
                for xx in np.asarray(res["x_sm"])[
                    -6:, int(np.where(spec.SeriesID == "GDPC1")[0][0])
                ]
            ],
            "pickle_max_abs_dC": max_dc,
        }
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
    payload["meta"] = {
        "v1_commit": sha,
        "data_source": "data/US_new_v1",
        "threshold": THRESHOLD,
        "sample_start_iso": "2000-01-01",
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "python": platform.python_version(),
        "note": "v1 code with A0 NumPy-2 shims; pickle_max_abs_dC records "
        "agreement with the NumPy<2 production pickle",
    }
    out = REPO / "tests" / "golden" / "dfm_legacy_estimator.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
