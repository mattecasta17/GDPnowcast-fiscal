# Code Quality Audit — GDPnowcast-fiscal

**Scope:** Python code quality, idioms, anti-patterns, modularity. Excludes folder structure and statistical/econometric methodology.

**Reviewed paths (absolute):**
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\Functions\` (8 files, ~1.8k LoC)
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\dashboard_nowcast_new.py` (1166 lines)
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\dashboard_nowcast_fiscal.py` (1469 lines)
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\nowcast_{2017,2024,2025}{,_fiscal}.py` (sampled, ~180 lines each)
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\DFM_new.py`, `DFM_fiscal.py`
- `C:\Users\Matteo17\OneDrive\Desktop\Repos\GDPnowcast-fiscal\variables_creation.py`

---

## TL;DR

- **`Functions/` is a near-literal MATLAB port** with MATLAB indexing tricks, MATLAB-style comments (`%`-feel), 1-based offsets, and `.copy()`-everything paranoia. It runs (probably), but it is largely opaque, untested, and fragile. Critical: `Functions/update_Nowcast2.py:6` imports `Functions.update_Nowcast.News_DFM` — **that module does not exist in the repo**, so every `nowcast_YYYY*.py` script is broken on a clean checkout.
- **A `Functions/__init__.py` is empty (1 line)** — the package has no public surface, so importers must spell out `Functions.dfm`, `Functions.load_spec`, etc. (cosmetic but inconsistent with the "library" framing).
- **The 18 `nowcast_YYYY[_fiscal].py` scripts are ~95% copy-paste**. `nowcast_2024.py` vs `nowcast_2024_fiscal.py` differs by ~5 lines (folder names + Spec filename). `nowcast_2017.py` vs `nowcast_2024.py` differs only by the year literals and the embedded vintage/parameter dicts. This is the single biggest tech-debt source.
- **Two ~1k–1.5k-line Streamlit dashboards (`dashboard_nowcast_new.py`, `dashboard_nowcast_fiscal.py`) are themselves ~80% copy of each other** (677 diff lines on a 2.5k-line base). Both are three giant `if/elif/else` branches with no functions, no caching (`@st.cache_data`), and re-imports of `matplotlib`/`numpy` mid-file.
- **Hardcoded absolute Windows paths to a OneDrive folder** (`C:\Users\Matteo17\OneDrive\Desktop\...`) appear in ~20 places across `nowcast_*.py` and `variables_creation.py`, plus a **plaintext FRED API key** committed in `variables_creation.py:25`. The repo will not run for any other user as-is.

---

## Per-File Assessment

### `Functions/dfm.py` — 1086 lines, 8 functions

**Severity: High** (correctness-critical and largely unreadable, but works)

- **MATLAB port artefacts everywhere.** Docstrings refer to `Par.blocks`, `Res.x_sm`, `f(t-1)` Matlab syntax. Comment styles are inconsistent (`#`, `# %`, leading docblocks). Several MATLAB conventions leak through, e.g. `flatten('F')` (Fortran order) and `reshape((..,..), order="F")` are used throughout to mimic MATLAB column-major behaviour — fine, but undocumented as a deliberate choice.
- **Function sizes.** `InitCond` (lines 213–430) is ~220 lines, `EMstep` (432–750) is ~320 lines. Both are dense matrix algebra interleaved with control flow. No internal helpers — they should each be broken into named sub-steps (e.g. `_estimate_observation_eq`, `_estimate_idiosyncratic_ar1`, `_compute_initial_variance`).
- **Defensive `.copy()` paranoia.** Every assignment ends with `.copy()` even when the source is immediately consumed (e.g. `C = C_new.copy()`, `R = R_new.copy()` at 130–133). This is clearly defensive translation from MATLAB pass-by-value semantics. Costs memory + readability; ~50 `.copy()` calls could go.
- **Cryptic naming and one-letter conventions inherited from MATLAB:** `nM, nQ, pC, ppC, r_i, rp1, t_start, idx_iM, idx_iQ, A_i, Q_i, BM, SQ, BQ, eyeN, ii_idio, n_idio_M, c_i_idio, bl_idxM, bl_idxQ, rps, no_c, R_con, q_con, Wt, Zu, Vu, VC, iF, VCF, J_1, J_2, VmT_1, ZmU, VmU, ZmT, S, m, k`. Some are unavoidable (math notation), but several (`temp`, `temp_init`, `e_idx`, `kk`, `xx_j`, `ff_j`, `iff_j`, `Cc`, `a1`, `a2`, `a3`) are throwaway.
- **Magic numbers.** `R_mat = np.array([2,-1,0,0,0,3,0,-1,0,0,2,0,0,-1,0,1,0,0,0,-1]).reshape((4,5))` (line 88) is the tent-aggregation constraint matrix and has zero explanation. `1e-4` covariance floors (lines 382, 746–747) appear unexplained. `19` divisor at line 408 (`sig_e = (Rdiag[nM:]/19)`) is undocumented.
- **Type hints: zero.**
- **`em_converged` has a bug at line 786:** `print('******likelihood decreased from {} to {}').format(previous_loglik,loglik)` — the `.format` is called on the **None return of `print`**, not on the string. This will raise `AttributeError: 'NoneType' object has no attribute 'format'`. Reachable only when log-lik decreases by >1e-3 with `check_decreased=1` (the default), so the bug is latent but real.
- **`max_iter = 5000` is set twice** (lines 10 default arg, 124 hardcoded reassignment) — the kwarg from `dfm(..., max_iter=...)` is silently ignored.
- **Print statements act as logging.** `dfm` prints tables 3–7 directly to stdout (lines 73–77, 180–209). Mixing presentation with estimation makes this function uncomposable. Should return the tables (or a `dataclass`) and let the caller print.
- **Inline `print(i)` debug leftover** at `Functions/remNaNs_spline.py:77` — should not be in a library function.

### `Functions/load_data.py` — 164 lines

**Severity: Medium**

- **Broken validation:** line 38 `ValueError("File is not an EXCEL FILE")` constructs an exception but **does not `raise` it** — the validation is silently a no-op. Same pattern at `load_data.py:148` and `summarize.py:119`. (`load_spec.py:68` does raise correctly.)
- **`transformData` has a closure-over-loop-variable bug shape.** The `formula_dict` dictionary is built at module-execution scope using `t1`, `step`, `n` (lines 117–121), which are NOT defined when the dict is constructed — they only exist inside the `for i in range(N)` loop that starts at line 125. Python treats them as late-binding free variables, so the lambdas pick up whatever the **last** iteration's `t1`/`step`/`n` were. Works only because in this file the dict is rebuilt-by-redeclaration in the right scope or because every call site resolves them — but the safer (and actually-Pythonic) form is to make them parameters: `lambda x, t1=t1, step=step, n=n: ...`. Definitely subtle and confusing.
- **`"lin": lambda x: x*2`** at line 116 looks suspiciously wrong (doubles every level?). Line 134 then takes the `lin` branch via `X[:,i] = Z[:,i].copy()` — so the lambda is never actually called, but its presence in the dict is misleading dead code.
- **Date arithmetic with magic `+ 366`.** `Time = dat.Date.apply(lambda x: x.toordinal()+366)` (line 68). MATLAB-day-number conversion. The docstring at the top of the file even calls it out ("we need to add 366 days to match with Matlab date numeric values") — so MATLAB-style date numbers are propagated through the whole codebase rather than using `pd.Timestamp` natively. Every downstream caller has to do `dt.fromordinal(Time[i] - 366)` to display dates. This is a pervasive smell.
- **`np.in1d` is deprecated** since NumPy 1.25 — use `np.isin` (line 77).
- **`if sample != None`** instead of `is not None` (line 55).

### `Functions/load_spec.py` — 98 lines

**Severity: Medium**

- Class name `load_spec` violates PEP 8 (should be `LoadSpec` or, better, just `Spec` since it is a data container).
- **Broken `raise` message** at line 68: `raise ValueError("{} raise ValueError(column missing from model specification.".format(field))` — the message text accidentally embeds the words `raise ValueError(` (copy-paste residue) and the parenthesis is unbalanced.
- **`raw.columns = [i.replace(" ","") for i in raw.columns]`** silently mutates user data — fine here, but worth a comment.
- **Print-on-construction** (line 95–99) — `load_spec()` prints "Table 1: Model specification" as a side effect. Bad for testing, importing in dashboards, etc.
- The `transformation` dict (lines 82–90) is **duplicated** in concept with `load_data.transformData`'s `formula_dict` (lines 116–123); the two should live in a single module-level constant.

### `Functions/decompose_common_factor.py` — 88 lines

**Severity: Medium**

- **Mixed Italian/English comments** (lines 14, 42, 53, 67) — inconsistent with the English-everywhere norm.
- Function name says "decompose common factor" but the function silently **writes a CSV to disk** (line 83) — side effect not in the contract. Returning the DataFrame and letting the caller decide where to write is the cleaner split.
- **`output_dir="common_residual_decomp"`** is a mutable-ish default (string) and a hardcoded folder name — better as a required arg or `Path`.
- The hardcoded `component_map` dict (17–39) is the same kind of data as `dashboard_nowcast_new.py`'s `fed_category_map` (58–86) but with different keys and grouping. **Two sources of truth** for the same C/I/NX/G/Other taxonomy.
- The `.assign(key=1).merge(... key=1)` cross-join pattern (line 81) is convoluted; `comp_w.assign(**df_summary.iloc[0].to_dict())` (or `pd.merge` on a cross join) reads better.

### `Functions/extract_common_residual.py` — 100 lines

**Severity: Medium**

- **Italian comments + emoji output** (`⚠️` at line 28, "Tronco a", "Calcola"). OK if intentional, but the rest of the project is bilingual-inconsistent.
- The function makes **assumptions about shape orientation** (lines 19–33) and self-transposes if needed. This kind of "smart" reshaping is a foot-gun; the caller should know what they're passing.
- **`res_skf.get("Pm")`, `res_skf.get("logL")`** (lines 48–49) — but `SKF` in `dfm.py` returns a dict with keys `"Vm"` and `"loglik"`, not `"Pm"` and `"logL"`. So `V` and `logL` here are silently `None` and never used. Dead/wrong code.
- `gdp_total = gdp_common` followed by `gdp_resid = 0.0` (lines 75–76) is set up so that `share_common = 1`, `share_residual = 0` always — the "decomposition" is degenerate. Likely an unfinished port from `decompose_common_factor.py`.

### `Functions/remNaNs_spline.py` — 146 lines

**Severity: Medium**

- **`method=2`/`method=4`/`method=5` are 90% the same code** (lines 76–96 vs 116–128 vs 133–145) repeated three times with minor changes. Extract `_spline_then_filter(x, k)` helper.
- **Stray `print(i)`** at line 77 inside an inner loop — debug leftover.
- `lfilter` boilerplate (`np.append(np.append(x[0]*np.ones((k,1)), x), x[-1]*np.ones((k,1)))`) is repeated 5 times verbatim.
- 5 numeric `method` codes with **no enum** and no docstring beyond the top blob. A `StrEnum`/`Literal["mean_fill", "spline_trim", ...]` would prevent typo bugs.

### `Functions/summarize.py` — 143 lines

**Severity: Medium**

- **`data_table_prep(option, ...)` with a numeric option dispatch (1, 2, 3, 4)** is an anti-pattern — should be four separate functions (`_format_time_range`, `_format_min_max`, `_format_frequency`, `_format_units`).
- **`builtin shadowing:** `min = Time[...]`, `max = Time[...]` at lines 103–104 shadow the built-ins.
- `ValueError("Option needed: must be 1 or 2")` at line 119 — same "unraised exception" bug as elsewhere (function says options 1–4, message says 1 or 2).
- `dt.fromordinal(... - 366)` MATLAB-date juggling repeated 4 times.

### `Functions/update_Nowcast2.py` — 111 lines

**Severity: Critical** (broken import on clean checkout) / **Medium** (rest)

- **Line 6: `from Functions.update_Nowcast import News_DFM`** — no such module in `Functions/`. The 18 nowcast scripts all transitively depend on this and will fail with `ModuleNotFoundError` immediately. Either the file was deleted accidentally, never committed, or the project relies on `MajesticKhan/Nowcasting-Python` being on `sys.path`. README does not document this.
- The `_old`/`_new`/`_rev` triple-call pattern to `News_DFM` (lines 63–64) plus 12-element tuple unpacking (`y_old, _, _, _, _, _, _, _, _ = News_DFM(...)`) is a strong code smell — the function returns 9 values, of which 7 are immediately discarded. The function is doing too much; should be split or return a dataclass.
- The "pad with 12 NaN months" block (lines 25–36) is undocumented magic.
- **Argument order is positional and long** (`X_old, X_new, Time, Spec, Res, series, period, vintage_old, vintage_new`) — would benefit from keyword-only args.
- File name violates PEP 8 (`update_Nowcast2.py`, mixed case + a "2" suffix). Suggests a v1 was discarded.

### `Functions/__init__.py` — 0 bytes

Empty file. Makes `Functions/` a package but exports nothing — every import is the verbose `from Functions.<module> import <name>`. Adding `from .dfm import dfm`, etc. would let callers do `from Functions import dfm`.

### `dashboard_nowcast_new.py` — 1166 lines, ~3 functions

**Severity: High** (maintainability)

- **Top-level imperative script**, not a Streamlit app. Three giant `if view_mode == "Single Quarter":` / `elif "Multi Quarter":` / `else:` branches with **zero function decomposition**. The "Multi Year" branch alone is 700+ lines (462–1158).
- **No caching.** A Streamlit app that re-reads every CSV and every Excel sheet on every interaction. `@st.cache_data` on the I/O is the obvious win — `pd.read_excel(news_file, sheet_name=sheet)` is called inside a double `for` loop (lines 388–389, 805–806).
- **Imports inside `for` loops / inside `if` blocks** (`import matplotlib.dates as mdates` at lines 309, 537; `import numpy as np` at lines 888–889, 989, 1230–1231, 1285–1286, 1425–1426). Each branch re-imports.
- **Function `last_friday()` defined twice** (lines 316 and 539) — same body. Define once at the top.
- **`q_periods` dict is redeclared 3 times** with identical content (lines 325, 552, 607, 661) — pure copy-paste.
- **The "load nowcast files, compute periods, plot" pattern** repeats 3 times (single year, 2017–2019, 2021–2025) — the only differences are the year filter and the title. A helper `plot_nowcast_evolution(year_range, ax, title)` would collapse ~300 lines into ~60.
- **Hardcoded "exclude 2020" everywhere** (lines 549, 604, 876, 967, 1009, 1071) — should be a single `EXCLUDE_YEARS = {"2020"}` constant.
- **Two ways to compute `gdp_actual`** scattered: `df_nowcast["y_new"].iloc[-1] + df_nowcast["error"].iloc[-1]` (line 131, 348, 576, 685, 728). Should be a function `compute_advance_release(df)`.
- **Inline HTML/markdown blobs** (lines 106–113, 1160–1165, 1059–1066, 1103–1109) — fine in Streamlit but accumulate.
- **Mixed plotting backends:** matplotlib + seaborn + plotly Express all used, sometimes for the same plot type. No consistent style.

### `dashboard_nowcast_fiscal.py` — 1469 lines

**Severity: High**

- **80% identical to `dashboard_nowcast_new.py`** (`diff` shows 677 lines of differences out of 2635 total — the rest is the same code). All inherited issues plus:
- **Three extra fiscal-specific sections at the end** (lines 1209–1461): "Fiscal Variable Impact by Quarter", "Fiscal Variables Seasonality", "Diebold–Mariano Tests". These are the only legitimate additions; everything before them is duplication.
- **The DM-test block** (lines 1324–1461) hardcodes path-mangling (`NOWCAST_DIR.replace("_fiscal", "")`) to find the baseline CSVs — fragile coupling between the two dashboards.

### `nowcast_2017.py`, `nowcast_2024.py`, `nowcast_2025.py` (and `_fiscal` siblings) — ~180 lines each

**Severity: High** (duplication)

- **18 near-identical files.** `diff nowcast_2024.py nowcast_2024_fiscal.py` shows ~10 line changes (folder names + spec filename + path suffixes). `diff nowcast_2017.py nowcast_2024.py` shows differences only in the embedded `gdp_adv_estimate`, `vintages_dict_*`, and `param_map_*` literals.
- **Hardcoded absolute Windows paths to OneDrive in every file** (e.g. `nowcast_2024.py:63`): `Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20231002.pickle")`. ~8 such paths per file × 18 files = ~144 hardcoded user-specific paths.
- **The `load_pickle_cached` helper is redefined in every file** (lines 87–92 in `_2024`, lines 88–93 in `_2017` with a different name `load_res_cached`) — should be a single utility in `Functions/`.
- **Variable naming inconsistency between siblings:** `nowcast_2017.py` calls the cache `_loaded_params` and the loader `load_res_cached`; `nowcast_2024.py` calls them `param_cache` and `load_pickle_cached`. Same code, different identifiers.
- **`vintages_dict` is named `vintages_dict` in 2017, `vintages_dict_2020` in 2020, `vintages_dict_2024` in 2024** — even the dict-variable name drifts.
- **`check_vintage_file` defined in `nowcast_2017.py:95` but never called.** Dead code; presumably an early debugging helper that the other years no longer carry.
- **`print(f"Saved nowcast_Q/nowcast_..._fiscal.csv")` in `nowcast_2024_fiscal.py:159`** says `nowcast_Q/` (non-fiscal folder) but the file is saved to `nowcast_Q_fiscal/`. Misleading log line — copy-paste artefact.
- **Broad `except Exception as e: print(...); continue`** at line 152 swallows everything (data load, numerical errors, anything).

### `DFM_new.py` — 166 lines, `DFM_fiscal.py` — 64 lines

**Severity: Medium**

- **`DFM_new.py` is mostly commented-out code** — ~100 of 166 lines are commented Plotly blocks (lines 49–73, 88–101, 104–166). The actual estimation is ~30 lines. Dead exploratory code should be deleted or moved to a notebook.
- **`DFM_fiscal.py` is `DFM_new.py` with the plot blocks deleted and a longer `vintages` list.** Otherwise identical control flow. Should be one parametrised script.
- **`DFM_fiscal.py:62`: file saved with bare `file_name` (no folder) despite `output_path = os.path.join(output_dir, file_name)` being computed on line 60 and then ignored.** Bug — outputs land in CWD instead of `DFM_quarter_param_fiscal/`.
- **`# TODO: Res and Spec should be separate, this will be fixed after the unit tests are created`** (line 85 `_new`, line 64 `_fiscal`) — there are no unit tests, so the TODO is open-ended.
- **`pickle.dump`** of model state is the persistence mechanism. Fragile across NumPy/SciPy versions; consider `joblib` or a structured dict-of-arrays + `np.savez`.

### `variables_creation.py` — 118 lines

**Severity: Critical** (security)

- **Line 25: `api_key = os.environ.get("FRED_API_KEY") or "64b47ef802cce7ec9c8b65d476e9a8ea"`** — FRED API key committed in plaintext as a fallback. Should be rotated and replaced with `assert os.environ.get("FRED_API_KEY"), "FRED_API_KEY env var required"`.
- **Line 11: `OUTPUT_DIR = Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\data\US_fiscal2")`** — hardcoded user-specific path.
- **Broad `except Exception as e:`** (line 53) — catches everything including KeyboardInterrupt prior to Python 3.8 (OK now, but still loses signal). The string-match retry logic (`"Too Many Requests" in msg or "Exceeded Rate Limit" in msg`) is brittle; check the response object instead.
- Italian print messages with emojis (`❌`, `⚠️`, `🔄`, `💾`, `✅`) intermixed.

---

## Recurring Patterns (Anti-Patterns)

### 1. **`ValueError(...)` constructed but not raised**

Appears in `load_data.py:38`, `load_data.py:148`, `summarize.py:119`. Validation is silently a no-op. Universal fix: `raise ValueError(...)`.

### 2. **MATLAB-date convention (`toordinal() + 366`) leaked into every date operation**

Forced on every caller: `dt.fromordinal(t - 366)`. Should be replaced with `pd.Timestamp` end-to-end (one-time refactor in `load_data.readData` + `update_Nowcast2.update_nowcast2` + `summarize.data_table_prep`).

### 3. **Defensive `.copy()` everywhere**

Translated from MATLAB pass-by-value semantics. ~80 occurrences in `dfm.py` alone. Most can be removed once true aliasing risks are identified.

### 4. **Numeric-option dispatch instead of polymorphism**

`remNaNs_spline(X, options={"method": 2, "k": 3})` with method ∈ {1,2,3,4,5}; `data_table_prep(option=1|2|3|4, ...)`. Use named functions or a `Literal[...]`.

### 5. **Hardcoded absolute Windows paths**

In every `nowcast_YYYY*.py` and in `variables_creation.py`. Make them relative or read from a `.env`/`config.py`.

### 6. **`except Exception: continue` / `except Exception: print(); continue`**

In `nowcast_*.py:152` and `variables_creation.py:53`. Silently eats errors.

### 7. **Side-effecting side-effects in library code**

`load_spec.__init__` prints. `dfm()` prints 4 tables. `decompose_common_factor` writes a CSV. Library functions should be pure or have their I/O behind an explicit flag (`verbose=False`).

### 8. **Empty package `__init__.py` + verbose absolute imports**

Every module imports `from Functions.dfm import dfm`. Re-export in `Functions/__init__.py`.

### 9. **No type hints, no docstrings in the modern sense**

The MATLAB-style docblocks document inputs/outputs as prose; Python type hints + numpydoc/Google style would make IDE tooling work.

### 10. **Duplicate domain dictionaries**

The C/I/NX/G/Other taxonomy lives in `decompose_common_factor.py:component_map` and `dashboard_nowcast_new.py:fed_category_map` (different keys, different grouping). Should be a single `Functions/categories.py`.

### 11. **Re-imports inside loops/branches**

`import matplotlib.pyplot as plt`, `import numpy as np`, `import matplotlib.dates as mdates` reappear inside conditionals in both dashboards. Move all imports to the top.

### 12. **Bug: `print(...).format(...)`**

`Functions/dfm.py:786`. Latent crash.

### 13. **Bug: missing import / dead-code references**

`Functions/update_Nowcast2.py:6` imports a missing module. `Functions/extract_common_residual.py` reads keys `"Pm"`/`"logL"` that `SKF` never returns.

---

## Quick Wins (Low Effort, High Impact)

1. **Run `ruff` / `pyflakes` over the repo.** Catches the unraised `ValueError`, the `print().format()` bug, unused imports, double-imports, `np.in1d` deprecation, and shadowed builtins (`min`, `max` in `summarize.py`) in one shot.
2. **Add the missing `Functions/update_Nowcast.py`** (or remove the broken import). Likely copy from the upstream `MajesticKhan/Nowcasting-Python` repo. Without this the nowcast scripts cannot run.
3. **Delete the API key fallback** in `variables_creation.py:25` and rotate the key.
4. **Replace 18 `nowcast_YYYY*.py` files with one** `nowcast.py --year 2024 --fiscal` that reads its `gdp_adv_estimate`, `vintages_dict`, `param_map` from a YAML/JSON config in `configs/`. The script body is identical; only the literal data differs.
5. **Replace absolute OneDrive paths with `Path(__file__).parent / "DFM_quarter_param" / f"ResDFM_{date}.pickle"`** — repo becomes portable in one search-and-replace.
6. **Remove all commented-out plotting blocks in `DFM_new.py`** (~100 lines) — they belong in a notebook.
7. **Move `last_friday()` and `q_periods` to the top of each dashboard** — kills 4 duplicates per file.
8. **Wrap every `pd.read_csv` / `pd.read_excel` in the dashboards with `@st.cache_data`.** Free perf win.
9. **Apply `black` / `ruff format`** with line length 100 for a consistent baseline.
10. **Rename `load_spec` → `Spec`** (the class) and `update_Nowcast2` → `news_decomposition` (the module).

---

## Strategic Refactors (Medium / Long Effort)

### A. **Collapse the 18 nowcast scripts into one CLI**

```
configs/
  nowcast_2024.yaml          # gdp_adv_estimate, vintages_dict, param_map, switch_dates
  nowcast_2024_fiscal.yaml
  ...
nowcast/__main__.py          # argparse: --config configs/nowcast_2024.yaml
nowcast/runner.py            # the (currently duplicated) loop body
nowcast/io.py                # load_pickle_cached, output paths
```

Yields ~150 lines instead of ~3200, and the configurations become version-controlled data.

### B. **Unify the two dashboards into one Streamlit app**

The fiscal/baseline split is a single boolean toggle in the sidebar. Most of the code is identical; the fiscal-specific tail (DM tests, fiscal-variable charts) can be conditionally rendered:

```python
include_fiscal = st.sidebar.checkbox("Include fiscal variables", value=False)
NOWCAST_DIR = "nowcast_Q_fiscal" if include_fiscal else "nowcast_Q"
...
if include_fiscal:
    render_dm_tests(...)
    render_fiscal_charts(...)
```

Plus: extract `render_single_quarter(df, metrics)`, `render_multi_quarter(...)`, `render_multi_year(...)` functions and a `load_quarter_data(quarter)` helper with `@st.cache_data`. Target: ~600 lines for one dashboard instead of ~2600 for two.

### C. **De-MATLAB the `Functions/` library**

A surgical pass, not a rewrite:
- Replace `Time = toordinal()+366` with `pd.DatetimeIndex` at the I/O boundary; delete every `- 366` downstream.
- Wrap `dfm()` printing in `if verbose:`; return tables as DataFrames.
- Break `InitCond` and `EMstep` into 3–4 named helpers each. (Be cautious — math correctness is hard to verify without tests, see "Risk Areas".)
- Add type hints at function signatures (`np.ndarray`, `Spec`, etc.).
- Replace the `options={"method": int, "k": int}` API of `remNaNs_spline` with explicit functions: `fill_with_filter`, `trim_trailing_then_spline`, `trim_trailing_only`, etc.

### D. **Add a thin test harness**

Even 5 golden-output tests (run `dfm` on one vintage, snapshot `Res["C"]` and `Res["loglik"]` final value) would catch any regression introduced by the refactors in (C). Currently the project has zero tests.

### E. **Replace pickled `ResDFM` with structured persistence**

`np.savez_compressed` of the arrays + a small JSON sidecar for `Spec` metadata. Decouples model artefacts from Python/NumPy versions and makes the files inspectable.

---

## Risk Areas (Refactor With Care)

- **`Functions/dfm.py:InitCond` and `EMstep`** — dense linear algebra ported from MATLAB with no tests. Any "clean-up" of `.copy()`, `flatten('F')`, or `reshape(..., order='F')` risks silently changing results (Fortran-vs-C order in NumPy is a frequent source of bugs). Before touching: pickle one `Res` from a known vintage as a regression fixture.
- **`Functions/update_Nowcast2.update_nowcast2`** — relies on the missing `News_DFM`. Once recovered, the news-decomposition math is the project's main contribution and is similarly untested.
- **`Functions/remNaNs_spline.py` method numbering (1–5)** — multiple call sites assume specific behaviour; the methods are partially redundant and `method 2` vs `method 4` differ in NaN-threshold (`>0.8` vs `==1.0`). Be sure all callers pass correct method numbers before consolidating.
- **The MATLAB date offset (`+366`/`-366`)** — touches every date-handling line in the project (`load_data`, `update_Nowcast2`, `summarize`, both dashboards, every nowcast script). A migration to `pd.Timestamp` must happen in one atomic PR or it will produce off-by-one-day errors.
- **`Functions/dfm.py:EMstep` line 664 comment** — `# POSSIBLE WEAK POINT FOUND: NEED TO TEST ON INDEXING AS NUMPY DOES NOT MAINTAIN PROPER MATRIX FORM DEPENDING ON HOW ITS INDEXED: CHECK` — flagged by the original MK porter as suspect. Anyone refactoring should treat this block as fragile.
- **The fiscal vs baseline dashboards being separate** is currently the only way to compare two sets of outputs (`NOWCAST_DIR.replace("_fiscal", "")` at line 1337 of fiscal dashboard does the cross-link). Unifying them must preserve the DM-test comparison logic.

---

## Code Excerpts

### Bug: `print().format()` will crash if log-lik decreases (`Functions/dfm.py:783–787`)

```python
if check_decreased == 1:
    if (loglik - previous_loglik) < -1e-3:
        print('******likelihood decreased from {} to {}').format(previous_loglik,loglik)
        decrease = 1
```

The `.format` is called on `None` (the return of `print`). Should be `print('...'.format(...))`.

### Bug: validation that does nothing (`Functions/load_data.py:37–38`)

```python
if not os.path.splitext(datafile)[1] in [".xlsx",".xls"]:
    ValueError("File is not an EXCEL FILE")
```

`ValueError` is constructed and discarded — never raised. Same pattern in `load_data.py:148` and `summarize.py:119`.

### Anti-pattern: massive copy-paste between sibling scripts

`nowcast_2024.py` vs `nowcast_2024_fiscal.py` differ in just the folder names and Spec filename:

```diff
- Spec   = load_spec('Spec_US_new.xlsx')
+ Spec   = load_spec('Spec_US_fiscal.xlsx')
- os.makedirs("nowcast_Q", exist_ok=True)
+ os.makedirs("nowcast_Q_fiscal", exist_ok=True)
- "prev": Path(r"...\DFM_quarter_param\ResDFM_20231002.pickle"),
+ "prev": Path(r"...\DFM_quarter_param_fiscal\ResDFM_fiscal_20231002.pickle"),
```

Across 18 files, this is the dominant maintenance hazard.

### Security: API key committed (`variables_creation.py:24–26`)

```python
def get_fred():
    api_key = os.environ.get("FRED_API_KEY") or "64b47ef802cce7ec9c8b65d476e9a8ea"
    return Fred(api_key=api_key)
```

Rotate immediately; replace with env-only.
