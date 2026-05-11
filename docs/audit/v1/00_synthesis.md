# GDPnowcast-fiscal — Synthesis of the 3-agent audit

**Date:** 2026-05-11
**Inputs:** `01_structure_audit.md`, `02_code_quality_audit.md`, `03_methodology_audit.md`

---

## Verdict (one paragraph)

The repo is **fixable, not throw-away**. The DFM core in `Functions/dfm.py` is a faithful Python port of the FRBNY Banbura-Modugno mixed-frequency DFM (Bok et al. 2018) and the pseudo-real-time vintage backtest (~450 weekly ALFRED snapshots) is **methodologically more disciplined than the average Master thesis**. The code around it is, however, undergraduate-quality: 18 near-clone scripts, 2 near-clone dashboards, no tests, no `.gitignore`, hardcoded Windows paths, a leaked FRED API key, and a broken import that makes the public repo **non-runnable on a clean checkout** — and therefore `Results.pdf` non-reproducible. More importantly, **3 methodology bugs may have inflated the headline result** and should be fixed before any presentation/publication, regardless of code refactoring.

---

## The three issue categories, ranked by what matters

| # | Category | Why it matters | Effort |
|---|---|---|---|
| 1 | **Methodology bugs that may change conclusions** | The thesis claim "fiscal variables improve nowcasting, especially in Q2 / post-2020" may not survive a clean re-run | 2–3 days investigative work + re-running backtests |
| 2 | **Reproducibility blockers** | Repo doesn't run as-published; FRED API key leaked | 0.5–1 day |
| 3 | **Code organization / duplication** | 18 nowcast scripts → 1; 2 dashboards → 1; `Functions/` → installable package | 4–6 days |

If you only have time for one category, **do (1)**. Refactoring messy-but-working code can wait. Re-running a thesis backtest with a quietly-wrong feature alignment cannot.

---

## Category 1 — Methodology bugs (highest priority)

All three flagged by the methodology agent; the structure/code-quality agents independently saw the symptoms (broken import, missing file).

### 1.1 GCEC1 is mis-aligned by 2 months vs GDPC1 (`variables_creation.py:96-97`)

```python
# Only GCEC1 is shifted forward by 2 months, GDPC1 is not
s = s.shift(2, freq="MS")
```

In FRED, both `GDPC1` and `GCEC1` are stamped quarter-start. The shift moves GCEC1 to quarter-end, but `GDPC1` stays at quarter-start. The DFM treats both as `Frequency == "q"` and applies the same 5-lag tent aggregator — so **GCEC1 ends up loading on the wrong quarter's tent**. Likely explanation for why GCEC1's contribution to nowcast updates is ~0 (0.003 vs 0.045 for the monthly deficit in `Results.pdf` Fig A7): the variable is contributing nothing because its information is being attributed to the wrong quarter.

**Fix:** Either shift both quarterly series consistently, or shift neither and let the loader handle alignment.
**Impact:** Could reveal that GCEC1 actually has a meaningful contribution (or confirm it doesn't — but currently you can't tell).

### 1.2 MTSDS133FMS loaded as raw levels (`Spec_US_fiscal.xlsx`, row 33)

`Transformation = lin` for the Monthly Treasury Statement deficit series. This series is:
- **Non-stationary** (federal deficits trend toward −$300B/month)
- **Highly seasonal** (April surplus from tax inflows)

A DFM standardises but does not deseasonalise. Loading this raw is methodologically wrong. The thesis's finding that "MTSDS133FMS has highest impact in Q2 because of tax season seasonality" is **partly an artefact** — the April spike is a calendar effect the model interprets as macro news.

**Fix:** Use `ch1` (12-month difference) or run X-13ARIMA-SEATS first.
**Impact:** The "Q2 fiscal effect" headline may not survive deseasonalisation.

### 1.3 Diebold-Mariano tests likely computed at weekly granularity, not quarterly

`Results.pdf` Table B5 reports `Observations = 575, 228, 347`. With 32 quarters × ~22 Friday vintages ≈ 700, these numbers betray **weekly-level DM**, not quarterly. Weekly forecast errors on the same target quarter are heavily serially correlated; HAC corrects partially but probably not enough. Honest quarterly-level DM (T ≈ 30) would likely show **borderline significance** rather than p ≈ 0.0001.

**Fix:** Re-run DM on quarterly final-week nowcasts only. Apply Harvey-Leybourne-Newbold (1997) small-sample correction or bootstrap.
**Impact:** "fiscal significantly improves" headline could weaken substantially.

### 1.4 W875RX1 is mis-labelled as "fiscal"

W875RX1 is *personal income excluding transfers* — an income/consumption variable, not a fiscal-policy variable. Worse: the baseline already includes DSPIC96 (Personal Income), with which W875RX1 has correlation > 0.95.

**Fix:** Either re-frame the contribution honestly (it's a marginal alternative income variable) or remove it from the "fiscal" block.

---

## Category 2 — Reproducibility blockers

### 2.1 Missing `Functions/update_Nowcast.py` — pipeline can't run on a clean clone

`Functions/update_Nowcast2.py:6` does `from Functions.update_Nowcast import News_DFM`. The module is not in the repo. Every `nowcast_YYYY*.py` script will fail with `ModuleNotFoundError` on a fresh clone. **All numbers in `Results.pdf` are therefore not reproducible from the public repo as-is.**

**Fix:** Either recover the file from a local backup, or inline `News_DFM` into `update_Nowcast2.py`. (Original likely from `MajesticKhan/Nowcasting-Python`.)

### 2.2 FRED API key committed in plaintext (`variables_creation.py:25`)

```python
api_key = os.environ.get("FRED_API_KEY") or "64b47ef802cce7ec9c8b65d476e9a8ea"
```

Already in git history on a public repo → effectively burned.
**Fix:** Rotate the key, remove the fallback, document `.env` setup in README.

### 2.3 144 hardcoded Windows paths

All 18 `nowcast_YYYY*.py` files contain `C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\...`. The repo is unusable on any other machine.
**Fix:** `Path(__file__).parent / "DFM_quarter_param" / ...` in one mechanical pass.

### 2.4 No `.gitignore`, 209 MB repo, 97 MB `.git`

70 pickle files, 1041 xlsx, 136 csv all committed.
**Fix:** Add `.gitignore` for `*.pickle`, `__pycache__/`, generated `outputs/`, `.env`.

### 2.5 Unpinned + incomplete `requirements.txt`

9 unpinned packages; `fredapi` and `python-dateutil` are imported but not listed. No Python version pin. No `pyproject.toml`.

---

## Category 3 — Code organization (lowest priority)

### 3.1 Massive duplication
- 18 `nowcast_YYYY[_fiscal].py` files, ~90% identical → can collapse to **one** `run_nowcast.py --year YYYY --variant {baseline,fiscal}` driven by `configs/vintages.yml` + `configs/gdp_truth.yml` extracted from the in-file dicts.
- 2 dashboards (1166 + 1469 lines), ~80% identical → one Streamlit app with a `variant` toggle.
- `DFM_new.py` + `DFM_fiscal.py` → one `estimate_dfm.py --variant`.

### 3.2 `Functions/` is a near-literal MATLAB port
- `dfm.py` is 1086 lines with MATLAB date numbers (`+ 366` / `- 366`) leaking everywhere
- Two 200+ line functions (`InitCond`, `EMstep`)
- ~80 defensive `.copy()` calls
- Latent bug at `dfm.py:786`: `print(...).format(...)` crashes on `None` (only triggers if log-lik decreases — rare but real)
- Non-PEP8 package name (`Functions/` instead of `gdpnowcast/`)

### 3.3 Dead / broken code
- `Functions/extract_common_residual.py` reads dict keys (`"Pm"`, `"logL"`) that `SKF` never returns → degenerate decomposition (`share_common = 1` always)
- `DFM_fiscal.py:62`: computes `output_path` then ignores it (saves to CWD instead of fiscal output dir)
- `nowcast_2024_fiscal.py:159`: log line says "nowcast_Q/" but writes to "nowcast_Q_fiscal/"
- Unraised `ValueError(...)` in `load_data.py:38, :148` and `summarize.py:119` → validation is a silent no-op
- ~70% of `DFM_new.py` is commented-out Plotly code

---

## Proposed target structure

```
gdpnowcast-fiscal/
├── README.md                  # install / fetch data / run / reproduce
├── pyproject.toml             # pinned deps, package metadata
├── .gitignore
├── .env.example               # FRED_API_KEY=
│
├── src/gdpnowcast/            # ex-Functions/
│   ├── dfm.py
│   ├── data.py                # ex-load_data.py
│   ├── spec.py                # ex-load_spec.py
│   ├── news.py                # ex-update_Nowcast2.py (+ recovered News_DFM)
│   ├── nans.py                # ex-remNaNs_spline.py
│   └── decomposition.py       # merge decompose_common_factor + extract_common_residual
│
├── configs/
│   ├── spec_us_baseline.xlsx  # ex-Spec_US_new.xlsx
│   ├── spec_us_fiscal.xlsx
│   ├── vintages.yml           # extracted from the 18 vintages_dict_YYYY
│   └── gdp_truth.yml          # extracted from the 18 gdp_adv_estimate
│
├── data/                      # GITIGNORED; fetched by scripts/fetch_data.py
├── outputs/                   # GITIGNORED; produced by scripts
│
├── scripts/
│   ├── fetch_fred.py          # ex-variables_creation.py (no hardcoded key)
│   ├── estimate_dfm.py        # --variant baseline|fiscal --vintage YYYY-MM-DD
│   ├── run_nowcast.py         # --year YYYY --variant baseline|fiscal
│   └── run_all.py             # loop years × variants
│
├── apps/
│   └── dashboard.py           # single Streamlit, --variant toggle
│
├── tests/
│   ├── test_dfm_smoke.py      # one vintage end-to-end golden output
│   ├── test_load_spec.py
│   └── test_news.py
│
└── docs/
    ├── thesis_results.pdf     # ex-Results.pdf
    └── methodology.md
```

---

## Phased plan

### Phase 0 — Methodology fixes (PRIORITY)
**Effort: 2–3 days investigative + N days re-running backtests**

- Restore `Functions/update_Nowcast.py` (or inline `News_DFM`).
- Verify GDPC1 / GCEC1 date alignment with an end-to-end unit test against BEA published Q-over-Q growth.
- Decide GCEC1 shift policy (shift both quarterly series or neither).
- Switch MTSDS133FMS transformation `lin` → `ch1` (or apply X-13ARIMA-SEATS).
- Re-compute DM tests on quarterly final-week nowcasts only (T ≈ 30 ex-2020).
- Add a non-DFM benchmark (Atlanta Fed GDPNow or ARMA(1,1)) for absolute interpretability.
- Re-write the "fiscal contribution" section honestly.

### Phase 1 — Safety + portability (quick wins)
**Effort: 0.5–1 day**

- Rotate FRED API key, remove plaintext fallback, add `.env.example`.
- Add `.gitignore` (pickles, `__pycache__`, `outputs/`, `.env`).
- Replace 144 absolute Windows paths with relative `Path(__file__).parent / ...`.
- Move `Results.pdf` → `docs/`.
- Delete orphan `data/yyyy-mm-dd.xls`.
- Pin `requirements.txt` versions, add missing `fredapi`, `python-dateutil`.
- Expand README with **Install / Fetch data / Run** sections.

### Phase 2 — Structural refactor
**Effort: 2–4 days**

- Rename `Functions/` → `src/gdpnowcast/`, add `pyproject.toml`, `pip install -e .`.
- Extract `vintages_dict_*` + `gdp_adv_estimate` from 18 scripts → `configs/vintages.yml` + `configs/gdp_truth.yml`.
- Collapse 18 nowcast scripts → 1 CLI (`scripts/run_nowcast.py`).
- Collapse `DFM_new.py` + `DFM_fiscal.py` → `scripts/estimate_dfm.py`.
- Collapse 2 dashboards → `apps/dashboard.py` with variant toggle + `@st.cache_data`.
- Move generated artifacts to `outputs/{variant}/{stage}/`, gitignore them.

### Phase 3 — Tests + CI + de-MATLAB
**Effort: 2–3 days**

- Add `tests/test_dfm_smoke.py` (one tiny vintage, snapshot `Res["C"]` + final loglik).
- Add `tests/test_load_spec.py`, `tests/test_news.py`.
- Fix `dfm.py:786` print bug, fix unraised `ValueError`s.
- Strip MATLAB date convention: replace `toordinal()+366` / `fromordinal()-366` with `pd.Timestamp` at the I/O boundary.
- Move `dfm()` print tables behind `verbose=True`.
- GitHub Actions: `pytest` + `ruff check`.

**Total: 7–11 working days** (Phase 0 is the only one that genuinely affects the validity of your thesis result).

---

## Recommendation

Start with **Phase 0**. The whole point of the project — does adding fiscal variables improve GDP nowcasting? — currently rests on 3 bugs that may have inflated the answer. Fixing those first, *before* presenting the work to Afonso or anyone external, is the highest-leverage action. Code prettiness is irrelevant if the headline number doesn't survive a clean re-run.

Phase 1 (safety) takes half a day and removes the API-key liability + makes the repo runnable for a hypothetical reviewer.

Phases 2 + 3 are pure software-engineering cleanup. Worth doing if you plan to extend the work (e.g. Staff Nowcast 2.0 features, more fiscal series, comparison to GDPNow) but can be deferred otherwise.
