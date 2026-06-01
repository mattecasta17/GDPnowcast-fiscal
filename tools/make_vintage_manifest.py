"""One-time dev tool: extract the real v1 vintage dates from data/US_*/ filenames
into committed manifests. Re-run only if the v1 vintage set on disk changes."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.xlsx$")
SOURCES = {"baseline": "US_new", "fiscal": "US_fiscal"}


def main() -> None:
    # D2: complete both variants to the canonical UNION of v1 vintage dates. v1's
    # fiscal set was missing 2021-01-04 (present in baseline); adding it gives both
    # variants the full, correct vintage set (486 each, identical date lists).
    found: dict[str, set[str]] = {}
    for variant, subdir in SOURCES.items():
        src = REPO_ROOT / "data" / subdir
        found[variant] = {m.group(1) for f in src.glob("*.xlsx") if (m := PATTERN.match(f.name))}
    canonical = sorted(found["baseline"] | found["fiscal"])
    for variant in SOURCES:
        out = REPO_ROOT / "configs" / f"vintages_{variant}.csv"
        out.write_text("vintage\n" + "\n".join(canonical) + "\n", encoding="utf-8")
        added = sorted(set(canonical) - found[variant])
        print(f"{variant}: {len(canonical)} vintages -> {out}  (added vs v1: {added})")


if __name__ == "__main__":
    main()
