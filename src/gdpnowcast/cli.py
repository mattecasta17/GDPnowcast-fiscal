"""Unified Typer CLI. Phase 2 wires `fetch`; later phases add estimate/run/etc."""

from __future__ import annotations

from pathlib import Path

import typer

from .data.builder import build_vintage, write_vintage
from .data.fred import fetch_release_history, get_fred
from .data.spec import SPEC_PATHS, load_spec
from .data.vintages import load_manifest

app = typer.Typer(add_completion=False, help="GDPnowcast-fiscal CLI")

_OUT_SUBDIR = {"baseline": "US_new", "fiscal": "US_fiscal"}
_DATA_ROOT = Path("data")


@app.callback()
def _main() -> None:
    """GDPnowcast-fiscal CLI. Keeps the multi-command structure (estimate/run come later)."""


@app.command()
def fetch(
    variant: str = typer.Option("fiscal", help="baseline (32 series) | fiscal (35)"),
    data_dir: Path = typer.Option(_DATA_ROOT, help="output root (gitignored)"),
    limit: int = typer.Option(0, help="only the first N vintages (0 = all; for smoke)"),
) -> None:
    """Rebuild ALFRED point-in-time vintage Excel files for a variant."""
    if variant not in SPEC_PATHS:
        raise typer.BadParameter(f"variant must be one of {sorted(SPEC_PATHS)}")
    specs = load_spec(SPEC_PATHS[variant])
    vintages = load_manifest(variant)
    if limit:
        vintages = vintages[:limit]
    out_dir = data_dir / _OUT_SUBDIR[variant]

    fred = get_fred()
    typer.echo(f"fetching {len(specs)} release histories from ALFRED ...")
    histories = {sp.series_id: fetch_release_history(fred, sp.series_id) for sp in specs}

    written = 0
    for v in vintages:
        if (out_dir / f"{v.isoformat()}.xlsx").exists():
            continue  # resumable checkpoint
        write_vintage(build_vintage(histories, specs, v), out_dir, v)
        written += 1
    typer.echo(f"done: {variant} -> {out_dir} ({written} new, {len(vintages)} total)")


if __name__ == "__main__":
    app()
