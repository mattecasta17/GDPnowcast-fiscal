# Verified — Bug #1: GCEC1 mis-aligned vs GDPC1

## Verdict

**REFUTED.** The `s.shift(2, freq="MS")` applied to GCEC1 in
`variables_creation.py:97` is not a bug — it is the *fix* that aligns GCEC1
into the same "third-month-of-quarter" convention that GDPC1 and ULCNFB
already follow in the vintage Excel files. After the shift, GDPC1, GCEC1,
and ULCNFB all sit on the same Mar/Jun/Sep/Dec rows and feed identically
into the Mariano-Murasawa tent. The audit's claim that "GDPC1 is on
2024-01-01, GCEC1 on 2024-03-01" is contradicted by direct inspection of
`data/US_fiscal/2024-10-04.xlsx`, in which **both** series share
2024-03-01, 2024-06-01, ….

The audit document itself acknowledges this on a later page (point 4 of
"Data pipeline issues",
`docs/audit/v1/03_methodology_audit.md:388-405`), which directly
contradicts the earlier "Bug #1" framing on lines 319-331 of the same
file. The earlier framing is wrong.

## Evidence

### The shift is GCEC1-only

`variables_creation.py:86-97`:

```python
86          for var in TARGET_SERIES:
87              freq = "Q" if var == "GCEC1" else "M"
88              print(f"  ➜ Aggiornamento {var}...")
89              s = fetch_fred_monthly_asof(fred, var, vintage_str, freq=freq)
90              s = s.loc[DATA_START:vd]
91
92              if s.empty:
93                  print(f"    ⚠️ Nessun dato per {var}")
94                  continue
95              # 🔄 Sposta GCEC1 di due mesi avanti, così finisce sull’ultimo mese del trimestre
96              if var == "GCEC1":
97                  s = s.shift(2, freq="MS")
```

`TARGET_SERIES = ["GCEC1", "MTSDS133FMS", "W875RX1"]` (`variables_creation.py:22`).
The script only writes these three series. Only GCEC1 is shifted, because it
is the only quarterly variable among them. The Italian comment translates as
"Shift GCEC1 forward by two months so it lands on the last month of the
quarter."

This is the *intended* behaviour: turn a FRED-native quarter-start stamp
(e.g. 2024-01-01) into a "last month of quarter" stamp (2024-03-01) so the
new series matches the convention already used elsewhere in the vintage file.

### GDPC1 is NOT shifted *here* — but it is also not fetched here

`Grep` for `\.shift\(` across the repo (only Python sources, excluding audit
markdown):

```
variables_creation.py:97:                s = s.shift(2, freq="MS")
```

Exactly one call. So GDPC1 is not shifted *by this script*. But GDPC1 is
also never *fetched* by this script: `TARGET_SERIES` does not include it.
GDPC1, ULCNFB, MTSDS133FMS (historical), etc. are pre-loaded into the
vintage Excel files via a separate (un-committed) ingestion pipeline that
already places them on the third month of each quarter.

The audit's bug-#1 framing implicitly assumes that GDPC1 would land on
2024-01-01 if it were fetched the same way as GCEC1 — but the actual
vintage file shows GDPC1 *already* on 2024-03-01.

### Vintage Excel confirms the dates are aligned, not misaligned

Reading `data/US_fiscal/2024-10-04.xlsx` directly:

```
          Date      GDPC1     GCEC1   ULCNFB
2   1985-03-01   8400.820  2120.284   60.898
5   1985-06-01   8474.787  2167.338   61.282
8   1985-09-01   8604.220  2216.743   61.406
11  1985-12-01   8668.188  2225.878   ...
...
458 2023-03-01  22403.435  3756.400  119.098
461 2023-06-01  22539.418  3783.653  119.837
464 2023-09-01  22780.933  3836.304  119.853
467 2023-12-01  22960.600  3870.720  119.005
470 2024-03-01  23053.545  3887.718  120.118
473 2024-06-01  23223.906  3917.049  120.245
```

Aggregate counts:

```
GDPC1 non-null rows: 158
GCEC1 non-null rows: 158
GDPC1 non-null AND GCEC1 null: 0
GCEC1 non-null AND GDPC1 null: 0
Distinct months in GDPC1 non-null rows:  {3, 6, 9, 12}
Distinct months in GCEC1 non-null rows:  {3, 6, 9, 12}
Distinct months in ULCNFB non-null rows: {3, 6, 9, 12}
```

Every quarterly variable shares the exact same set of dates. There is no
mis-alignment in the actual data file the DFM ingests.

### The DFM tent treats every q-series identically

`Functions/load_data.py:125-131`:

```python
125    for i in range(N):
126        formula = Spec.Transformation[i]
127        freq    = Spec.Frequency[i]
128        step    = Freq_dict[freq] # time step for different frequencies based on monthly time
129        t1      = step -1         # assume monthly observations start at beginning of quarter (subtracted 1 for indexing)
130        n       = step/12         # number of years, needed to compute annual % changes
131        series  = Spec.SeriesName[i]
```

With `Freq_dict = {"m":1,"q":3}` (line 115), every q-series gets
`step=3, t1=2`. The `pca` branch then writes results at rows `2, 5, 8, …`:

`load_data.py:143-144`:

```python
143        elif formula == 'pca':
144            X[t1::step, i] = formula_dict['pca'](Z[:, i].copy())
```

Rows 2, 5, 8, … = months Mar, Jun, Sep, Dec (0-indexed from a Jan-start
monthly grid). So the DFM expects quarterly values to live on the third
month of the quarter — **exactly the convention the shift produces.**
Without the shift, GCEC1 would be on rows 0, 3, 6, … and `pca` would read
NaN for every quarter.

The tent constraint is in `Functions/dfm.py` and applies the
`[1,2,3,2,1]` Mariano-Murasawa weights to every q-series identically:

`dfm.py:369-370`:

```python
369    # Monthly-quarterly agreggation scheme
370    C    = np.hstack([C,np.vstack([np.zeros((nM,5*nQ)),np.kron(np.eye(nQ),np.array([1,2,3,2,1]).reshape((1,-1)))])])
```

`dfm.py:715-717` (EM update for quarterly variables):

```python
715        nom -= np.matmul(Wt,np.matmul(np.matmul(np.array([[1,2,3,2,1]]), Zsmooth[i_idio_jQ][:,[t+1]]),
716                                      Zsmooth[bl_idxQ_ind][:,[t+1]].T) + \
717                            np.matmul(np.array([[1,2,3,2,1]]),Vsmooth[t+1][np.ix_(i_idio_jQ,bl_idxQ_ind)]))
```

`dfm.py:722-724` (BGR equation 13 constraint):

```python
722        C_i_constr = C_i - np.matmul(np.matmul(np.matmul(np.linalg.inv(denom),R_con_i.T),
723                                               np.linalg.inv(np.matmul(np.matmul(R_con_i,np.linalg.inv(denom)),R_con_i.T))),
724                                     np.matmul(R_con_i,C_i)-q_con_i)
```

There is no branching on series name; both GDPC1 and GCEC1 are members of
`idx_iQ` and pass through this code identically. This part of the audit
is correct — but the implication ("therefore the model can't know GCEC1
was pre-shifted") is moot because, after the shift, no per-series
correction is needed: both series live on the same row positions.

### Simulation confirming the shift produces the correct dates

```python
>>> idx = pd.date_range('2024-01-01', '2024-12-01', freq='QS')   # FRED-native
>>> s = pd.Series([100,101,102,103], index=idx)
>>> s
2024-01-01    100
2024-04-01    101
2024-07-01    102
2024-10-01    103
>>> s.shift(2, freq='MS')
2024-03-01    100   # ← matches GDPC1's 2024-03-01 in the vintage Excel
2024-06-01    101
2024-09-01    102
2024-12-01    103
```

So the FRED-native value for Q1 2024 (originally stamped 2024-01-01) ends
up stamped 2024-03-01, sharing the row with the existing GDPC1 Q1 2024
observation.

## Magnitude assessment

The shift is two months *within the same quarter* — Q1 2024 GDP refers to
Jan-Feb-Mar 2024, and the project's convention stores it on the *last*
month of that quarter (2024-03-01). FRED's native stamp puts it on the
*first* month (2024-01-01). Both stamps belong to the same calendar
quarter; the disagreement is purely about which monthly row the quarterly
value occupies. The shift +2 months never crosses a quarter boundary.

What about the tent (`[1,2,3,2,1]`)? The tent at row `t` aggregates the
*previous five* monthly values into one quarterly observation, with peak
weight on `t` (the publication month) and tapering weights on `t-1, t-2,
t+1, t+2`. With Q1 2024 on row 2024-03-01:

- weight 3 on March (= 2024 Q1 publication month, ✓)
- weight 2 on Feb and April (straddling quarter end)
- weight 1 on Jan and May

This is precisely the Mariano-Murasawa construction. If GCEC1 had stayed
on 2024-01-01, the EM update at quarterly rows would have read NaN from
the data matrix `Z` (via the `pca` formula indexed at `t1::step =
2::3 = {2, 5, 8, …}`), so GCEC1 would have been effectively dropped from
estimation — *not* "lagged by one quarter inside the factor structure"
as the audit claims. The pre-shift behaviour would be observationally
indistinguishable from setting `Model=0` for GCEC1.

So the practical effect of the shift is: GCEC1 is correctly ingested,
not corrupted. Removing the shift would silently *delete* GCEC1's
contribution to the model rather than misalign it.

## Notes / caveats

1. **The audit contradicts itself.** Bug #1 (lines 319-331 of
   `03_methodology_audit.md`) claims GDPC1 is on 2024-01-01 and GCEC1 is
   on 2024-03-01 → mis-alignment. Bug #4 of the "Data pipeline issues"
   section (lines 388-405 of the same file) admits GDPC1 is on
   2024-03-01 in the vintage Excel. The first framing is incorrect; the
   second is correct.

2. **The real ambiguity is the off-by-one between FRED's quarter-start
   convention and the project's last-month-of-quarter convention.** This
   is genuinely confusing and would benefit from documentation, but it
   is *internally consistent* once you accept the project uses last-month
   stamping. The `pca` transform indices (rows 2, 5, 8, … = Mar/Jun/Sep/Dec)
   confirm last-month is the intended convention.

3. **A real concern that the audit *does* flag legitimately:** there is no
   unit test that verifies `pca(GDPC1)` matches BEA-published Q-over-Q
   annualised growth rates. Such a test would catch any future
   off-by-one regression. This is worth adding even though the current
   alignment is correct.

4. **GCEC1's near-zero nowcast impact in Figure A7 must have a different
   explanation.** The audit attributes the 0.003 impact to mis-alignment.
   Since alignment is fine, the more plausible explanations are:
   (a) GCEC1 is quarterly so it arrives once every 3 months → most
   nowcast updates have no GCEC1 news to contribute;
   (b) GCEC1 (real govt consumption + gross investment) is a slow-moving
   series that is mostly tracked by the other real-sector variables
   (GDPC1 itself, DSPIC96, INDPRO, PCEC96, etc.) so its idiosyncratic
   news content is small;
   (c) Possible scale / standardisation effects: the DFM standardises
   inputs, so a low-variance series contributes proportionally little
   to factor updates even if its loading is non-zero.

5. **The shift uses `freq="MS"` (month start anchored).** This is
   correct for the project's monthly index built with
   `pd.date_range(..., freq="MS")` (line 34 of `variables_creation.py`).

## Commands run

```powershell
# 1. Read the shift site
Read variables_creation.py  (lines 1-119)

# 2. Search all .shift( in the repo
Grep "\.shift\("  → only variables_creation.py:97 in Python sources

# 3. Inspect the vintage file
python -c "import pandas as pd; df = pd.read_excel(r'data/US_fiscal/2024-10-04.xlsx'); \
  print(df[['Date','GDPC1','GCEC1','MTSDS133FMS','ULCNFB']].tail(15).to_string())"

# 4. Confirm GDPC1 and GCEC1 share dates
python -c "import pandas as pd; df = pd.read_excel(r'data/US_fiscal/2024-10-04.xlsx'); \
  print(sorted(set(pd.to_datetime(df.loc[df['GDPC1'].notna(),'Date']).dt.month))); \
  print(sorted(set(pd.to_datetime(df.loc[df['GCEC1'].notna(),'Date']).dt.month)))"
# → both print [3, 6, 9, 12]

# 5. Inspect the tent and pca indexing
Read Functions/load_data.py  (lines 88-153)
Read Functions/dfm.py         (lines 350-430)
Read Functions/dfm.py         (lines 600-725)

# 6. Confirm both series are q-frequency with pca transform
python -c "import pandas as pd; df = pd.read_excel('Spec_US_fiscal.xlsx'); \
  print(df[df['SeriesID'].isin(['GDPC1','GCEC1','ULCNFB'])].to_string())"
# → both GDPC1 and GCEC1 have Frequency='q', Transformation='pca'

# 7. Simulate the shift on a FRED-native series to confirm dates
python -c "import pandas as pd; \
  idx = pd.date_range('2024-01-01','2024-12-01',freq='QS'); \
  s = pd.Series([100,101,102,103], index=idx); \
  print(s.shift(2, freq='MS'))"
# → 2024-03-01, 2024-06-01, 2024-09-01, 2024-12-01
```
