"""One-off generator: extract per-quarter QuarterCfg data from the v1 nowcast_YYYY.py
scripts via AST (no code execution), so the Phase-4 registry is byte-exact rather than
hand-transcribed (~726 vintage date strings across 33 quarters).

Emits JSON to stdout:
    {"registry": {period: {vintages, gdp_actual, prev_vintage, curr_vintage, switch_date}},
     "fiscal_diffs": {period: {baseline, fiscal}}}

The BASELINE scripts are the canonical calendar. The fiscal scripts carry the same
calendar/params but with at least one known typo (2017q3 last vintage = 2017-10-28, a
Saturday, vs the baseline 2017-10-27 Friday -- no Saturday file exists, so v1 silently
dropped it). We therefore build the registry from baseline and REPORT fiscal diffs rather
than asserting equality; the runner is variant-agnostic (data_subdir/spec_file args), so
one baseline-derived registry serves both variants.

``advance_date`` is intentionally absent -- it comes from ALFRED (first realtime_start of
the quarter's GDP), recomputed/asserted by tools/build_headline_vintages.

prev/curr vintage = the pickle filename date (ResDFM[_fiscal]_YYYYMMDD.pickle -> YYYY-MM-DD);
the v2 runner re-estimates params from that DATA vintage instead of loading v1's pickle.

Usage (from repo root):
    uv run python -m tools.extract_quarter_configs
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
YEARS = range(2017, 2026)
_PICKLE_RE = re.compile(r"ResDFM(?:_fiscal)?_(\d{4})(\d{2})(\d{2})\.pickle")


def _assign_value_prefix(tree: ast.Module, prefix: str) -> ast.expr:
    """Value of the single module-level assignment whose target name starts with prefix.

    Asserts exactly one match (baseline uses ``vintages_dict``, fiscal ``vintages_dict_2017``;
    each script has one ``param_map_*`` / one ``gdp_adv_estimate``) so a future second match
    can't be silently picked.
    """
    matches = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id.startswith(prefix) for t in node.targets)
    ]
    assert (
        len(matches) == 1
    ), f"expected exactly 1 assignment matching {prefix!r}, got {len(matches)}"
    return matches[0]


def _pickle_to_date(call: ast.expr) -> str:
    """ast Path(r'...ResDFM[_fiscal]_YYYYMMDD.pickle') -> 'YYYY-MM-DD'."""
    assert isinstance(call, ast.Call), ast.dump(call)
    (arg,) = call.args
    assert isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    m = _PICKLE_RE.search(arg.value)
    assert m, f"no ResDFM_YYYYMMDD in {arg.value!r}"
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _parse_param_map(node: ast.expr) -> dict[str, dict[str, str]]:
    """param_map dict literal whose values mix Path(...) calls and str literals."""
    assert isinstance(node, ast.Dict)
    out: dict[str, dict[str, str]] = {}
    for k, v in zip(node.keys, node.values, strict=True):
        assert isinstance(k, ast.Constant)
        assert isinstance(v, ast.Dict)
        entry: dict[str, str] = {}
        for ik, iv in zip(v.keys, v.values, strict=True):
            assert isinstance(ik, ast.Constant)
            if ik.value in ("prev", "curr"):
                entry[ik.value] = _pickle_to_date(iv)
            elif ik.value == "switch_date":
                assert isinstance(iv, ast.Constant)
                entry[ik.value] = iv.value
        out[k.value] = entry
    return out


def _extract(path: Path) -> dict[str, dict]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    gdp = ast.literal_eval(_assign_value_prefix(tree, "gdp_adv_estimate"))
    vintages = ast.literal_eval(_assign_value_prefix(tree, "vintages_dict"))
    params = _parse_param_map(_assign_value_prefix(tree, "param_map"))
    return {
        period: {
            "vintages": list(vintages[period]),
            "gdp_actual": float(gdp[period]),
            "prev_vintage": params[period]["prev"],
            "curr_vintage": params[period]["curr"],
            "switch_date": params[period]["switch_date"],
        }
        for period in vintages
    }


def build_registry() -> tuple[dict[str, dict], dict[str, dict]]:
    """Return (canonical baseline registry, fiscal-vs-baseline diffs). advance_date absent."""
    registry: dict[str, dict] = {}
    fiscal_diffs: dict[str, dict] = {}
    for year in YEARS:
        base = _extract(REPO / f"nowcast_{year}.py")
        try:
            fisc = _extract(REPO / f"nowcast_{year}_fiscal.py")
        except Exception as exc:  # report, don't crash the generator
            fisc = {}
            fiscal_diffs[f"{year} (fiscal parse error)"] = {"error": repr(exc)}
        for period, b in base.items():
            if fisc.get(period) != b:
                fiscal_diffs[period] = {"baseline": b, "fiscal": fisc.get(period)}
        registry.update(base)
    return registry, fiscal_diffs


def main() -> None:
    registry, fiscal_diffs = build_registry()
    print(json.dumps({"registry": registry, "fiscal_diffs": fiscal_diffs}, indent=2))
    print(f"\n# {len(registry)} quarters; {len(fiscal_diffs)} fiscal diff(s)", flush=True)


if __name__ == "__main__":
    main()
