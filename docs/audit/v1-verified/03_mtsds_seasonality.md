# Verified — Bug #2: MTSDS133FMS un-deseasonalised

## Verdict

**CONFIRMED.** `MTSDS133FMS` (FRED's *Not Seasonally Adjusted* Federal Surplus/Deficit series) is loaded with `Transformation = 'lin'`, which is implemented as a pass-through copy of raw values. Neither `load_data.py` nor `dfm.py` apply any seasonal adjustment. The April tax-receipt spike is empirically the only positive month of the year and amounts to ~1.1 standard deviations of the cross-sectional series; it propagates directly into the DFM input and into Q2 nowcasts.

## Evidence

### Spec confirms `lin` transformation

`Spec_US_fiscal.xlsx`, row 33 (0-indexed; matches the audit's reference):

| Field | Value |
|---|---|
| Model | 1 |
| SeriesID | `MTSDS133FMS` |
| SeriesName | `Federal Surplus or Deficit [-]` |
| Frequency | `m` |
| Block1-Global | 1 |
| Block2-Soft | 0 |
| Block3-Real | 1 |
| Block4-Labor | 0 |
| **Transformation** | **`lin`** |
| Units | `$, Millions` |
| Category | Fiscal |

The series is loaded into Block1-Global and Block3-Real, in raw monthly levels.

### `lin` does no detrending/deseasonalisation

`Functions/load_data.py`, lines 116 and 133-134 (verbatim):

```python
116:    formula_dict = {"lin":lambda x:x*2,
                        "chg":lambda x:np.append(np.nan,x[t1+step::step] - x[t1:-1-t1:step]),
                        ...
```

```python
125:    for i in range(N):
126:        formula = Spec.Transformation[i]
127:        freq    = Spec.Frequency[i]
128:        step    = Freq_dict[freq] # time step for different frequencies based on monthly time
129:        t1      = step -1         # assume monthly observations start at beginning of quarter (subtracted 1 for indexing)
130:        n       = step/12         # number of years, needed to compute annual % changes
131:        series  = Spec.SeriesName[i]
132:
133:        if formula == 'lin':
134:            X[:,i] = Z[:,i].copy()
```

The `lin` branch is a direct copy of the raw column (`Z[:,i]`) into the DFM input matrix `X[:,i]`. No differencing, no log, no seasonal filter, no calendar adjustment. (The `lambda x: x*2` registered in `formula_dict` on line 116 for `"lin"` is dead code — it is never invoked because the `if/elif` chain on line 133 short-circuits to the simple copy. That is a separate code-quality concern but harmless here.)

The docstring at line 103 explicitly says `'lin' = Levels (No Transformation)`.

### The DFM applies no seasonal adjustment internally

Grep for `season|seasonal|x13|x-13|X13|deseason|detrend` across `Functions/` returns **no matches** (case-insensitive). The only seasonal-adjustment-aware code in the whole repo lives in `dashboard_nowcast_fiscal.py` lines 1269-1315, and that is a diagnostic plot ("Seasonal Volatility of Fiscal Variables") — not a transformation applied to model inputs.

What `dfm.py` does to the inputs is simple per-column standardisation (`Functions/dfm.py`, lines 92-94):

```python
92:    Mx   = np.nanmean(X,axis = 0)
93:    Wx   = np.nanstd(X,axis = 0,ddof = 1)
94:    xNaN = (X - np.tile(Mx,(T,1))) / np.tile(Wx,(T,1))
```

Subtracting the full-sample mean and dividing by the full-sample std does NOT remove seasonality — a recurring April spike survives unchanged because it has the same sign and magnitude every year.

### Empirical seasonality is real

Source: `data/US_fiscal/2024-10-04.xlsx`, column `MTSDS133FMS`, 1985-01 to 2024-08 (478 monthly observations, NaNs dropped).

**Month-of-year mean ($ Millions), full sample 1985-2024:**

| Month | Mean | Std | Min | Max | n |
|---|---:|---:|---:|---:|---:|
| Jan |     7,084 |  45,703 | -162,832 |  118,699 | 40 |
| Feb |  -125,978 |  90,975 | -310,922 |  -21,053 | 40 |
| Mar |  -104,459 | 118,674 | -659,592 |  -13,813 | 40 |
| **Apr** | **+59,117** | **159,955** | -737,851 |  308,215 | 40 |
| May |   -92,392 |  85,835 | -398,821 |   -3,611 | 40 |
| Jun |   -27,934 | 150,470 | -864,074 |  116,501 | 40 |
| Jul |   -76,370 |  73,034 | -302,050 |    5,061 | 40 |
| Aug |   -84,842 |  83,288 | -380,080 |   89,256 | 40 |
| Sep |     8,642 |  92,869 | -429,673 |  119,116 | 39 |
| Oct |   -72,441 |  57,581 | -284,071 |   -7,656 | 39 |
| Nov |   -90,412 |  72,619 | -314,012 |  -16,937 | 39 |
| Dec |   -16,785 |  44,209 | -143,562 |   53,220 | 39 |

April is, by a wide margin, the only month with a meaningfully positive average (`+$59.1 B`). Jan and Sep are very mildly positive (~$7-9 B), all other months average deficits between $-17 B and $-126 B.

**Last 10 years (2014-2024) — same pattern, more extreme:**

| Month | Mean | Std |
|---|---:|---:|
| Jan |       150 |  72,216 |
| Feb |  -231,030 |  42,436 |
| Mar |  -210,518 | 176,009 |
| **Apr** | **+59,773** | **296,334** |
| May |  -172,030 | 115,134 |
| Jun |  -133,257 | 258,313 |
| Jul |  -148,795 |  83,892 |
| Aug |  -154,867 | 116,514 |
| Sep |   -34,670 | 170,897 |
| Oct |  -120,410 |  68,862 |
| Nov |  -170,946 |  79,388 |
| Dec |   -46,933 |  52,561 |

The 2019-2024 raw print also visually confirms the pattern: April 2022 (+$308 B), April 2023 (+$176 B), April 2024 (+$210 B) are all large positives while neighbouring months are deeply negative. April 2020 and 2021 are exceptions (COVID stimulus dominated the tax-receipt cycle), which itself is informative — the seasonality is a structural calendar artefact that the model sees as a "signal" except when it gets overwhelmed by a true macro shock.

## Magnitude assessment

Three measures of how big the April effect is:

1. **Absolute dollar gap.**
   - Full sample: April mean = +$59 B, non-April mean = −$62 B → gap = **$121 B/month**.
   - Last 10 years: April mean = +$60 B, non-April mean = −$131 B → gap = **$190 B/month**.

2. **In units of the series' own standard deviation** (which is what the DFM sees after standardisation):
   - Full sample: gap / overall_std = $120,733 / $109,659 = **1.10 σ**.
   - Last 10 years: gap / overall_std = $190,400 / $168,208 = **1.13 σ**.

   So after standardisation the DFM is fed a ~1.1 σ recurring spike every April. For comparison, a typical macro shock to a stationary series is rarely larger than 2-3 σ; a 1.1 σ deterministic seasonal pattern is enormous.

3. **Quarterly aggregation (relevant for the Q2 finding).** Quarterly means of the raw monthly series (last 10 years):

   | Q | Mean ($M) | Std |
   |---|---:|---:|
   | Q1 (J-F-M) | -147,133 | 152,088 |
   | **Q2 (A-M-J)** | **-81,838** | **251,067** |
   | Q3 (J-A-S) | -115,218 | 134,831 |
   | Q4 (O-N-D) | -112,763 |  83,467 |

   Q2 is **the least-deficit quarter on average, by $33-65 B**, and the standard deviation is highest because of how variable the April figure is across years. This is exactly the signature of "Q2 = April spike artefact." A tent-aggregator over 5 monthly lags (the Mariano-Murasawa weighting `[1, 2, 3, 2, 1]/9` standard in DFM nowcasting) puts the largest weights on the middle months of the target quarter and the lag distribution still loads on April for Q2, mechanically pulling Q2 fiscal-block estimates upward whenever April rolls into the dataset.

4. **Validation of the fix.** Re-running with the audit's recommended `ch1` transformation (12-month difference):

   | Month | Mean (raw, $M) | Mean (ch1, $M) |
   |---|---:|---:|
   | Apr | +59,773 | +8,785 |
   | Non-Apr avg | -130,627 | -13,676 |
   | April-vs-other gap | **+190,400** | **+22,462** |
   | gap / std | **+1.13 σ** | **+0.12 σ** |

   `ch1` reduces the April seasonal gap by ~9× in standard-deviation terms. That confirms `ch1` (or proper X-13-ARIMA-SEATS) is a valid fix; the bug is real and tractable.

**Is the magnitude consistent with the audit's ~0.06 RMSE Q2 effect?** Yes, plausibly. A 1.1 σ recurring spike in a Block1+Block3 input series, propagated through the DFM and weighted by the tent aggregator into Q2 GDP nowcasts, can easily move per-vintage Q2 nowcast errors by 0.05-0.10 percentage points when other inputs are mid-vintage and the fiscal block carries non-trivial loadings. The audit's claimed 0.06 RMSE gap is well within the order of magnitude implied by the standardised gap; a more precise number would require a counterfactual rerun with `ch1` substituted in, but the mechanism is real and the size is right.

## Notes / caveats

- **The audit slightly understates one thing.** It says April is "a surplus spike" — true on the mean, but the *variance* in April is also the largest of any month (full-sample std = $160 B vs ~$70-150 B in other months). This makes April both a deterministic seasonal effect AND a high-variance month for genuine policy/legislative effects. So `lin` is wrong because (a) the deterministic part is treated as news, AND (b) the genuine April news is mis-scaled relative to other months by the full-sample standardisation. `ch1` fixes (a); X-13-ARIMA-SEATS would fix both more cleanly.

- **Audit is correct that `lin` does literally nothing.** Line 134 is verbatim a copy.

- **Vintage files contain the raw series only.** Inspection of `variables_creation.py` shows vintages are pulled directly from FRED via `fred.get_series('MTSDS133FMS', realtime_start=..., realtime_end=...)` with no post-processing. FRED's `MTSDS133FMS` is the Not-Seasonally-Adjusted variant; the seasonally-adjusted equivalent would be a different series ID and is not used anywhere in the repo. So there is no "hidden" pre-transformed copy.

- **`GCEC1` (Real Government Consumption & Investment) in row 32 uses `pca` (% change at annual rate),** which is appropriate; that fiscal-block input is fine. Only `MTSDS133FMS` is misconfigured.

- **The same `lin`-on-NSA pattern should be audited for other variables**, but a spec-wide grep is out of scope here. `W875RX1` (row not checked here in detail, but it appears in `variables_creation.py`'s `TARGET_SERIES`) would warrant a follow-up check.

- **`dfm.py` standardisation is per-column over the full sample.** Because of this, even adding more April data each year does not change the mean/std much, so the seasonal contamination is structurally persistent, not a small-sample artefact.

## Commands run

Re-verification recipe (PowerShell + Python, from repo root):

```bash
# 1. Spec row 33 inspection
python -c "import pandas as pd; s=pd.read_excel('Spec_US_fiscal.xlsx'); print(s.iloc[33].to_dict())"
# expected: {... 'SeriesID': 'MTSDS133FMS', 'Frequency': 'm', 'Transformation': 'lin', ...}

# 2. Grep for seasonal adjustment code paths
# (None expected outside the dashboard diagnostic.)
# Files searched: Functions/*.py
# Pattern: season|seasonal|x13|x-13|X13|deseason|detrend (case-insensitive)
# Result: zero matches in Functions/.

# 3. lin = copy
# Functions/load_data.py lines 133-134:
#     if formula == 'lin':
#         X[:,i] = Z[:,i].copy()

# 4. Standardisation only in dfm.py lines 92-94 (mean/std, no seasonal).

# 5. Empirical month-of-year stats
python -c "
import pandas as pd
df = pd.read_excel('data/US_fiscal/2024-10-04.xlsx')[['Date','MTSDS133FMS']].dropna()
df['Date']=pd.to_datetime(df['Date']); df['Month']=df['Date'].dt.month
print(df.groupby('Month')['MTSDS133FMS'].agg(['mean','std','count']).round(0))
"

# 6. ch1 fix sanity check
python -c "
import pandas as pd
df = pd.read_excel('data/US_fiscal/2024-10-04.xlsx')[['Date','MTSDS133FMS']].dropna()
df['Date']=pd.to_datetime(df['Date']); df=df.sort_values('Date').reset_index(drop=True)
df['ch1'] = df['MTSDS133FMS'] - df['MTSDS133FMS'].shift(12)
df['Month']=df['Date'].dt.month
print(df.dropna().groupby('Month')['ch1'].agg(['mean','std']).round(0))
"
```
