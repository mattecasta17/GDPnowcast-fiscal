# Verified — Reproducibility blockers

Verification date: 2026-05-11. Branch: `refactor/v2`. HEAD: `c351c75`.

## Finding A — Missing `Functions/update_Nowcast.py`

**Verdict:** CONFIRMED (with one nuance — the file existed on `main` history but was explicitly deleted; see Notes).

### Evidence

1. **File absent at HEAD.** `git ls-tree -r HEAD Functions/` lists 9 files; only `update_Nowcast2.py` is present, no `update_Nowcast.py`:

   ```
   Functions/__init__.py
   Functions/decompose_common_factor.py
   Functions/dfm.py
   Functions/extract_common_residual.py
   Functions/load_data.py
   Functions/load_spec.py
   Functions/remNaNs_spline.py
   Functions/summarize.py
   Functions/update_Nowcast2.py
   ```

   `Glob Functions/update_Nowcast*.py` returns only `Functions\update_Nowcast2.py`.

2. **Broken import is real.** `Functions/update_Nowcast2.py:6` reads, verbatim:

   ```python
   from Functions.update_Nowcast import News_DFM
   ```

   And uses it at lines 63–64:

   ```python
   y_old, _, _, _, _, _, _, _, _ = News_DFM(X_old, X_rev, Res, t_nowcast, i_series)
   y_rev, y_new, _, actual, forecast, weight, _, _, _ = News_DFM(X_rev, X_new, Res, t_nowcast, i_series)
   ```

3. **All 18 root nowcast scripts depend on this transitively.** A Grep for `from Functions.update_Nowcast2|import update_Nowcast2` on the project root matches every single `nowcast_YYYY*.py`:

   | Script | Line | Import |
   |---|---|---|
   | `nowcast_2017.py` | 4 | `from Functions.update_Nowcast2 import update_nowcast2` |
   | `nowcast_2017_fiscal.py` | 4 | same |
   | `nowcast_2018.py` | 4 | same |
   | `nowcast_2018_fiscal.py` | 4 | same |
   | `nowcast_2019.py` | 4 | same |
   | `nowcast_2019_fiscal.py` | 4 | same |
   | `nowcast_2020.py` | 4 | same |
   | `nowcast_2020_fiscal.py` | 4 | same |
   | `nowcast_2021.py` | 4 | same |
   | `nowcast_2021_fiscal.py` | 4 | same |
   | `nowcast_2022.py` | 4 | same |
   | `nowcast_2022_fiscal.py` | 4 | same |
   | `nowcast_2023.py` | 4 | same |
   | `nowcast_2023_fiscal.py` | 4 | same |
   | `nowcast_2024.py` | 4 | same |
   | `nowcast_2024_fiscal.py` | 4 | same |
   | `nowcast_2025.py` | 4 | same |
   | `nowcast_2025_fiscal.py` | 4 | same |

   Each one will fail at import time on a clean clone with `ModuleNotFoundError: No module named 'Functions.update_Nowcast'`.

4. **`News_DFM` is not defined anywhere else at HEAD.** A repo-wide Grep for `News_DFM` returns matches only inside (a) `Functions/update_Nowcast2.py` (the broken import + two call-sites), and (b) audit/design docs under `docs/`. No `def News_DFM` or `class News_DFM` anywhere at HEAD.

### Notes — git-history nuance not mentioned in v1 audit

`Functions/update_Nowcast.py` **was committed and later deleted** on the `main` history:

- Added in commit `729b40b "Nowcast"` (2025-12-03 17:07:55 UTC) — 431 lines, contained `def News_DFM(X_old, X_new, Res, t_fcst, v_news):` at line 122 plus `def update_nowcast` (line 10) and `def para_const` (line 347).
- Deleted in commit `e0928d5 "Nowcast"` (2025-12-03 17:23:10 UTC, ~16 minutes later) along with `.idea/` files. Deletion stat: `Functions/update_Nowcast.py | 431 -------`.

So this is not "never committed" — it was explicitly removed. The deletion looks accidental (bundled with an `.idea/` cleanup commit titled just "Nowcast"). Two implications:

- The fix is recoverable from local git history: `git show 729b40b:Functions/update_Nowcast.py` returns the full file. The v2 plan's contingency of "recover from `MajesticKhan/Nowcasting-Python`" is not needed — the original code is in this repo's own history.
- Both `729b40b` and `e0928d5` are reachable from `main` and `refactor/v2` (confirmed via `git branch --contains`), so the blob will not be GC'd as long as those branches exist.

The reproducibility blocker for an end-user cloning the public repo and running `pip install -r requirements.txt && python nowcast_2024.py` is real and total — none of the 18 root scripts can even import.

## Finding B — FRED API key leaked in source

**Verdict:** CONFIRMED.

### Evidence

1. **The literal key is at `variables_creation.py:25`**, verbatim:

   ```python
   api_key = os.environ.get("FRED_API_KEY") or "64b47ef802cce7ec9c8b65d476e9a8ea"
   ```

2. **Repo-wide Grep for the literal string `64b47ef802cce7ec9c8b65d476e9a8ea`** at HEAD returns 6 hits:
   - `variables_creation.py:25` — the actual occurrence in source
   - `docs/audit/v1/00_synthesis.md:79`
   - `docs/audit/v1/01_structure_audit.md:130`
   - `docs/audit/v1/02_code_quality_audit.md:164`
   - `docs/audit/v1/02_code_quality_audit.md:344`
   - `docs/audit/v1/03_methodology_audit.md:371`

   The five doc hits are the v1 audit citing the same line. The key itself appears in source exactly once.

3. **Git history — introduction commit:** `git log -p --all -- variables_creation.py` shows the key was introduced in **commit `729b40b "Nowcast"` (2025-12-03 17:07:55 UTC)** — the same commit that originally added `update_Nowcast.py`. It is the only commit touching `variables_creation.py`. The key has been in the repo since first commit of this file.

4. **No `.gitignore`, no `.env`, no `.env.example`** at the repo root:

   ```
   $ ls -la .gitignore .env .env.example
   ls: cannot access '.gitignore': No such file or directory
   ls: cannot access '.env':       No such file or directory
   ls: cannot access '.env.example': No such file or directory
   ```

   So even if a developer had created a local `.env`, it would have been committed by default.

### Notes

- The repo has remote `origin/main` on GitHub (visible from `git branch -a` showing `remotes/origin/main`, `remotes/origin/claude/bartender-portfolio-site-6G2gW`, etc.) and at least one merged PR (`#1`). The audit's claim that the key is "burned" because it sat in a public GitHub repo is reasonable. The key must be rotated regardless of whether the source line is now changed, because git history retains the value.
- The fix isn't just `Edit variables_creation.py` — it needs (a) rotate the FRED key at FRED's portal, (b) replace the fallback with a hard `assert`/`raise`, (c) add `.gitignore` + `.env.example`, and (d) consider history rewrite (`git filter-repo`) or accept that the burned key is permanently in history and rely on rotation.

## Reproduction commands run

```
# Finding A
ls Functions/
git ls-tree -r HEAD Functions/
Glob: Functions/update_Nowcast*.py
Glob: nowcast_*.py
Read Functions/update_Nowcast2.py (lines 1-20)
Grep "News_DFM" (repo-wide, content mode)
Grep "from Functions\.update_Nowcast|from update_Nowcast|import update_Nowcast" (content mode)
git log --all --diff-filter=A --name-only -- Functions/update_Nowcast.py
git log --all --diff-filter=D --pretty=format:"%H %s %ad" -- Functions/update_Nowcast.py
git show 729b40b:Functions/update_Nowcast.py | grep -nE "^def |^class |News_DFM"
git show e0928d5 --stat
git branch -a --contains 729b40b
git branch -a --contains e0928d5

# Finding B
Read variables_creation.py
Grep "64b47ef802cce7ec9c8b65d476e9a8ea" (repo-wide, content mode)
git log -p --all -- variables_creation.py | grep -n "FRED_API_KEY\|64b47ef802cce7ec9c8b65d476e9a8ea\|^commit\|^Date"
ls -la .gitignore .env .env.example
```
