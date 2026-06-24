"""Derive the fiscal-block ablation ladder for the dashboard.

Network-free. Reads the committed heavy-run output ``ablation/ablation_results.json`` (the
(advance-1) headline nowcasts of the three subset models M1/M2/M3, produced once by
``ablation/run_ablation.py``) plus the macro-only (``baseline.json``) and all-three
(``fiscal.json``) headlines, and writes ``docs/dashboard_data/ablation.json``: per-model
RMSE/MAE/bias (ex-2020) and DM-HLN tests vs macro-only and vs all-three.

The ladder isolates which fiscal series the model needs: the deficit alone, deficit+income,
deficit+govt, all three. (M0 macro-only == baseline.json, M4 all-three == fiscal.json -- not
recomputed.)

Usage (from repo root):
  uv run python -m tools.build_ablation
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from gdpnowcast.diebold_mariano import diebold_mariano

REPO = Path(__file__).resolve().parents[1]
DD = REPO / "docs" / "dashboard_data"
ABL = REPO / "ablation" / "ablation_results.json"
OUT = DD / "ablation.json"

# The ladder, in order. ``source`` is where each model's per-quarter errors come from:
# baseline/fiscal jsons for the endpoints, the ablation run for the three subsets.
MODELS = [
    {"id": "macro", "label": "Macro-only", "fiscal": [], "source": "baseline"},
    {"id": "deficit", "label": "+ Deficit", "fiscal": ["MTSDS133FMS"], "source": "M1_deficit_only"},
    {
        "id": "deficit_income",
        "label": "+ Deficit + Income",
        "fiscal": ["MTSDS133FMS", "W875RX1"],
        "source": "M2_deficit_income",
    },
    {
        "id": "deficit_govt",
        "label": "+ Deficit + Govt",
        "fiscal": ["MTSDS133FMS", "GCEC1"],
        "source": "M3_deficit_govt",
    },
    {
        "id": "all",
        "label": "All three",
        "fiscal": ["MTSDS133FMS", "W875RX1", "GCEC1"],
        "source": "fiscal",
    },
]


def _load(name: str) -> dict:
    return json.loads((DD / f"{name}.json").read_text(encoding="utf-8"))


def _dm_pair(e: np.ndarray, ref: np.ndarray) -> dict:
    sq = diebold_mariano(list(e**2), list(ref**2), 1)
    ab = diebold_mariano(list(np.abs(e)), list(np.abs(ref)), 1)
    return {
        "squared": {"dm": round(sq.dm_stat, 3), "p": round(sq.p_value, 3)},
        "absolute": {"dm": round(ab.dm_stat, 3), "p": round(ab.p_value, 3)},
    }


def build() -> dict:
    base = _load("baseline")
    fisc = _load("fiscal")
    abl = json.loads(ABL.read_text(encoding="utf-8"))

    err: dict[str, dict[str, float]] = {
        "baseline": {r["period"]: r["error"] for r in base["headline"]},
        "fiscal": {r["period"]: r["error"] for r in fisc["headline"]},
    }
    for key in ("M1_deficit_only", "M2_deficit_income", "M3_deficit_govt"):
        err[key] = {r["period"]: r["error"] for r in abl[key] if r["headline"] is not None}

    periods = [r["period"] for r in base["headline"] if not r["period"].startswith("2020")]
    for m in MODELS:
        missing = [p for p in periods if p not in err[m["source"]]]
        if missing:
            raise ValueError(f"{m['source']}: missing headline for {missing}")

    e_macro = np.array([err["baseline"][p] for p in periods])
    e_all = np.array([err["fiscal"][p] for p in periods])

    models: list[dict] = []
    for m in MODELS:
        e = np.array([err[m["source"]][p] for p in periods])
        models.append(
            {
                "id": m["id"],
                "label": m["label"],
                "fiscal": m["fiscal"],
                "rmse": round(float(np.sqrt((e**2).mean())), 3),
                "mae": round(float(np.abs(e).mean()), 3),
                "bias": round(float(e.mean()), 3),
                "dm_vs_macro": None if m["id"] == "macro" else _dm_pair(e, e_macro),
                "dm_vs_all": None if m["id"] == "all" else _dm_pair(e, e_all),
            }
        )

    return {
        "convention": (
            f"Headline (advance-1) ex-2020 (n={len(periods)}). Each model = the shared macro panel "
            "plus the listed fiscal series, on the same US_fiscal data with the DFM re-estimated. "
            "dm_vs_macro / dm_vs_all are DM-HLN (h=1) loss-differential tests of this model against "
            "the macro-only Staff Nowcast and against the all-three model (A=this model, B=ref; "
            "dm<0 => this model has lower loss). Source: ablation/run_ablation.py."
        ),
        "n_ex_2020": len(periods),
        "models": models,
    }


def main() -> None:
    bundle = build()
    OUT.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}  ({bundle['n_ex_2020']} quarters ex-2020)")
    for m in bundle["models"]:
        vs = (
            ""
            if m["dm_vs_macro"] is None
            else f" vs-macro MAE p={m['dm_vs_macro']['absolute']['p']}"
        )
        print(f"  {m['label']:20s} RMSE={m['rmse']} MAE={m['mae']}{vs}")


if __name__ == "__main__":
    main()
