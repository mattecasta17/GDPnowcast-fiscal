# GDPnowcast-fiscal — v2

> A mixed-frequency dynamic factor model (Banbura-Modugno / FRBNY Staff Nowcast) for U.S. real GDP, with a fiscal-variable extension. Master's thesis re-do, research-grade.

[![CI](https://github.com/mattecasta17/GDPnowcast-fiscal/actions/workflows/test.yml/badge.svg?branch=refactor/v2)](https://github.com/mattecasta17/GDPnowcast-fiscal/actions/workflows/test.yml)

> **Developed with AI-assisted tooling.** Every methodology choice and the full v1 bug-fix audit are documented in [`docs/audit/`](docs/audit/) and reproduced by the test suite — run `just ci` to verify lint, types, and tests in one command.

**Status:** v2 complete on branch `refactor/v2`. The implementation lives in `src/gdpnowcast/`; the v1 code was decommissioned in the Phase 5b cleanup (its behaviour is pinned by the committed golden tests, and git history preserves the files). See `docs/plans/2026-05-11-v2-design.md` for the design and phase roadmap.

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

The data layer rebuilds all point-in-time ALFRED weekly vintages from the committed manifests
(`configs/vintages_{baseline,fiscal}.csv`):

```bash
just fetch baseline                # or: uv run gdpnowcast fetch --variant baseline
just fetch fiscal
```

This re-creates `data/US_new/` and `data/US_fiscal/` (gitignored) from the FRED ALFRED API, with
strict as-of reconstruction (no revisions, no fills). The pre-advance cutoff vintages are built by
`uv run python -m tools.build_headline_vintages`.

## Run

The full 2017-2025 pseudo-real-time backtest (per-quarter weekly paths + the pre-advance headline
nowcast) writes the committed artifacts in `docs/dashboard_data/`:

```bash
just run fiscal                    # or: uv run python -m tools.run_backtest --variant fiscal
just run baseline
```

Variant comparison (Diebold-Mariano, power/MDE) and benchmarks are regenerated with
`uv run python -m tools.compare_variants` and `uv run python -m tools.run_benchmarks`.

## Dashboard

A static **Next.js** dashboard lives in [`apps/dashboard/`](apps/dashboard/). It renders the
pseudo-real-time backtest — headline nowcast vs the BEA advance, the within-quarter weekly path,
DFM-vs-naive benchmarks, and the fiscal-vs-baseline comparison — from a committed JSON bundle, with
no server or runtime data fetch.

```bash
npm install --prefix apps/dashboard
npm run dev --prefix apps/dashboard      # http://localhost:3000
npm run build --prefix apps/dashboard    # static export -> apps/dashboard/out
```

The bundle is regenerated from the committed backtest artifacts with
`uv run python -m tools.build_dashboard_data`; details in [`apps/dashboard/README.md`](apps/dashboard/README.md).

**Live:** [gdpnowcast-fiscal.vercel.app](https://gdpnowcast-fiscal.vercel.app)

---

## Repository layout

```
src/gdpnowcast/        # v2 importable package (Phase 1+ scaffold)
tests/                 # pytest suite
configs/               # spec_us_*.xlsx + runtime.toml (Phase 2+)
apps/dashboard/        # Next.js static dashboard (Phase 5)
data/                  # gitignored, built by `gdpnowcast fetch`
docs/                  # design docs, audits, plans, paper sources
  ├── plans/           # v2 design + per-phase implementation plans
  ├── audit/v1/        # 2026-05-11 audit reports
  ├── audit/v1-verified/  # 2026-05-11 verification reports
  └── README_v1.md     # original v1 README (historical)
```

The v1 implementation (`DFM_new.py`, `dashboard_nowcast_*.py`, `nowcast_YYYY*.py`, `Functions/`, `variables_creation.py`) was removed in the **Phase 5b cleanup** after the v2 port reproduced it exactly (pinned by the committed golden tests in `tests/golden/`); git history preserves the files. `Spec_US_*.xlsx` remain at root: they are the live model specifications read by the v2 pipeline.

---

## Documentation

- `docs/plans/2026-05-11-v2-design.md` — full v2 design doc, phase roadmap, methodology decisions
- `docs/audit/v1/00_synthesis.md` — original 3-agent audit of v1
- `docs/audit/v1-verified/00_synthesis.md` — verification of audit findings (some refuted, some confirmed)
- `RESUME.md` — current state of the refactor; read this first when resuming work

---

## License

See [LICENSE](LICENSE).
