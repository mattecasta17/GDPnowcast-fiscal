from datetime import date
from pathlib import Path

import pytest

from gdpnowcast.data.vintages import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
_DIRS = {"baseline": "US_new", "fiscal": "US_fiscal"}


def _built(variant: str) -> set[date]:
    d = REPO_ROOT / "data" / _DIRS[variant]
    return {date.fromisoformat(f.stem) for f in d.glob("*.xlsx")} if d.exists() else set()


@pytest.mark.parametrize("variant", ["baseline", "fiscal"])
def test_generated_is_superset_of_manifest(variant: str) -> None:
    # Gate on the v1 backup dir: it is created by Task 9 Step 1 right before the
    # full fetch, so its presence means data/<dir>/ now holds OUR generated files
    # (not the v1 files still on disk pre-fetch). Skip until then.
    backup = REPO_ROOT / "data" / f"{_DIRS[variant]}_v1"
    if not backup.exists():
        pytest.skip(f"{variant}: full fetch not run yet (no _v1 backup; see Task 9)")
    built = _built(variant)
    manifest = set(load_manifest(variant))
    missing = sorted(manifest - built)
    assert not missing, f"{variant}: {len(missing)} manifest vintages not generated: {missing[:10]}"
