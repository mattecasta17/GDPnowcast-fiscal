# justfile — task runner. Run `just` with no args to list recipes.

# On Windows, just defaults to `sh` (absent on native Windows); use PowerShell instead.
# On Linux/macOS (incl. CI), the default `sh` is used. Recipes call `uv run ...`, shell-agnostic.
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# Run the fast offline unit tests (excludes network-bound `slow` tests).
test:
    uv run pytest -m "not slow" -v --cov=gdpnowcast --cov-report=term-missing --cov-fail-under=0

# Run the slow/network tests (ALFRED point-in-time cross-validation; needs FRED_API_KEY in .env).
test-slow:
    uv run pytest -m slow -v

# Run the heavy port-verification tests: golden parity (dfm/news/runner) + the B6
# decomposition sanity check. Need the local v1 data backup (data/US_new_v1); CI
# skips them. The goldens are also `slow`, so this selects `golden or slow` and
# excludes the network ALFRED tests (those live in `test-slow`).
test-golden:
    uv run pytest -m "golden or slow" --ignore=tests/test_fetch_integration.py -v

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

# Phase 2 — rebuild ALFRED vintage files. `just fetch fiscal` or `just fetch baseline`.
fetch variant="fiscal":
    uv run gdpnowcast fetch --variant {{variant}}

# Full 2017-2025 backtest for one variant; writes docs/dashboard_data/{variant}.json.
run variant="fiscal":
    uv run python -m tools.run_backtest --variant {{variant}}

# Next.js dashboard dev server (http://localhost:3000).
dashboard:
    npm run dev --prefix apps/dashboard

# Composite — what CI runs.
ci: lint typecheck test
