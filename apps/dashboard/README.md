# GDP Nowcast - dashboard

Static [Next.js](https://nextjs.org/) dashboard for the GDPnowcast-fiscal v2 backtest: a dynamic
factor model nowcasting US GDP growth in pseudo real time, with a fiscal-augmented variant and
naive benchmarks. It reads a single consolidated JSON bundle produced by the Python pipeline and
renders it as fully static HTML (no server, no runtime data fetch).

## Stack

- Next.js 15 (App Router, `output: "export"` -> fully static `out/`)
- React 18 + TypeScript + Tailwind CSS
- Recharts for the charts (wrapped in a custom `ChartFrame` for reliable sizing)

## Data

The dashboard imports `src/data/dashboard.json` at build time. That file is **generated** from the
committed backtest artifacts by the Python tool in the repo root:

```bash
# from the repo root (regenerates src/data/dashboard.json)
uv run python -m tools.build_dashboard_data
```

`dashboard.json` consolidates `docs/dashboard_data/{baseline,fiscal,comparison,benchmarks}.json`
(headline series, weekly within-quarter paths, metrics, Diebold-Mariano tests, power/MDE,
benchmarks) plus a small set of data-derived "findings". It is committed so the dashboard builds
without the Python toolchain.

## Develop

```bash
npm install
npm run dev      # http://localhost:3000
```

## Build (static export)

```bash
npm run build    # emits ./out (static HTML/JS/CSS)
```

## Deploy

Any static host works. On [Vercel](https://vercel.com/) the project auto-detects Next.js and
serves the static export; set the **root directory** to `apps/dashboard`. No environment variables
are required.

> The figures are honest, look-ahead-safe pseudo-real-time results - see the in-page methodology
> section and the repo's `docs/` for the full evaluation design.
