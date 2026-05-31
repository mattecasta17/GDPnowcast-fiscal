# justfile — task runner. Run `just` with no args to list recipes.

# On Windows, just defaults to `sh` (absent on native Windows); use PowerShell instead.
# On Linux/macOS (incl. CI), the default `sh` is used. Recipes call `uv run ...`, shell-agnostic.
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# Run unit tests (smoke for now; grows in Phase 3).
test:
    uv run pytest -v --cov=gdpnowcast --cov-report=term-missing --cov-fail-under=0

# Run ruff lint + format check (no fixes; CI parity).
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Apply ruff fixes + formatting (use locally before committing).
fmt:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Type-check the v2 package only (v1 is excluded in pyproject.toml).
typecheck:
    uv run mypy src/gdpnowcast/ tests/

# Refresh the venv from pyproject.toml + uv.lock.
sync:
    uv sync --all-extras

# Phase 2 deliverable — placeholder.
fetch:
    @echo "gdpnowcast fetch is not implemented yet (Phase 2)."
    @exit 1

# Phase 5 deliverable — placeholder.
run:
    @echo "gdpnowcast run is not implemented yet (Phase 5)."
    @exit 1

# Phase 5 deliverable — placeholder.
dashboard:
    @echo "streamlit dashboard is not implemented yet (Phase 5)."
    @exit 1

# Phase 8 deliverable — placeholder.
paper:
    @echo "paper LaTeX build is not implemented yet (Phase 8)."
    @exit 1

# Composite — what CI runs.
ci: lint typecheck test
