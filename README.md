# GDPnowcast-fiscal — v2

> A mixed-frequency dynamic factor model (Banbura-Modugno / FRBNY Staff Nowcast) for U.S. real GDP, with a fiscal-variable extension. Master's thesis re-do, research-grade.

[![CI](https://github.com/mattecasta17/GDPnowcast-fiscal/actions/workflows/test.yml/badge.svg?branch=refactor/v2)](https://github.com/mattecasta17/GDPnowcast-fiscal/actions/workflows/test.yml)

> **Developed with AI-assisted tooling.** Every methodology choice and the full v1 bug-fix audit are documented in [`docs/audit/`](docs/audit/) and reproduced by the test suite — run `just ci` to verify lint, types, and tests in one command.

**Status:** v2 refactor in progress on branch `refactor/v2`. The v1 implementation lives at root (`DFM_new.py`, `Functions/`, `nowcast_YYYY*.py`, ...) and remains runnable. v2 lives in `src/gdpnowcast/` and is being built phase by phase — see `docs/plans/2026-05-11-v2-design.md` for the roadmap.

The v1 README is preserved at [`docs/README_v1.md`](docs/README_v1.md).

---

## Install

Prerequisites: Python 3.13, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), git.

```bash
git clone https://github.com/mattecasta17/GDPnowcast-fiscal.git
cd GDPnowcast-fiscal
git checkout refactor/v2          # while v2 is in development
uv sync --all-extras              # creates .venv, installs all deps
cp .env.example .env              # then edit .env and add your FRED_API_KEY
```

Verify the install:

```bash
just test                          # smoke test passes
just lint                          # ruff is happy
```

## Fetch

> **Not yet implemented — coming in Phase 2.**

In v2, the data layer rebuilds all FRED/ALFRED weekly vintages from scratch:

```bash
just fetch                         # or: uv run gdpnowcast fetch
```

This re-creates `data/vintages/{baseline,fiscal}/` from the FRED ALFRED API. The v1 vintage files in `data/` (gitignored) will eventually be regenerable and not committed.

## Run

> **Not yet implemented — coming in Phase 5.**

```bash
just run                           # or: uv run gdpnowcast run --year 2024 --variant fiscal
```

Until Phase 5 ships, use the v1 scripts directly (e.g. `python nowcast_2024_fiscal.py`). `Functions/update_Nowcast.py` is committed (recovered from git `729b40b`), so the v1 pipeline imports cleanly on a fresh clone — a full backtest still needs the FRED data fetched locally.

## Dashboard

> **Not yet implemented — coming in Phase 5.**

```bash
just dashboard                     # or: uv run streamlit run apps/dashboard.py
```

v1 dashboards (`dashboard_nowcast_new.py`, `dashboard_nowcast_fiscal.py`) still exist at root for reference.

---

## Repository layout

```
src/gdpnowcast/        # v2 importable package (Phase 1+ scaffold)
tests/                 # pytest suite
configs/               # spec_us_*.xlsx + runtime.toml (Phase 2+)
apps/                  # Streamlit dashboard (Phase 5)
data/                  # gitignored, built by `gdpnowcast fetch`
docs/                  # design docs, audits, plans, paper sources
  ├── plans/           # v2 design + per-phase implementation plans
  ├── audit/v1/        # 2026-05-11 audit reports
  ├── audit/v1-verified/  # 2026-05-11 verification reports
  └── README_v1.md     # original v1 README (historical)
```

v1 files (`DFM_new.py`, `dashboard_nowcast_*.py`, `nowcast_YYYY*.py`, `Functions/`, `Spec_US_*.xlsx`, `variables_creation.py`) stay at the repo root for now and will be migrated/deleted in Phase 3.

---

## Documentation

- `docs/plans/2026-05-11-v2-design.md` — full v2 design doc, phase roadmap, methodology decisions
- `docs/audit/v1/00_synthesis.md` — original 3-agent audit of v1
- `docs/audit/v1-verified/00_synthesis.md` — verification of audit findings (some refuted, some confirmed)
- `RESUME.md` — current state of the refactor; read this first when resuming work

---

## License

See [LICENSE](LICENSE).
