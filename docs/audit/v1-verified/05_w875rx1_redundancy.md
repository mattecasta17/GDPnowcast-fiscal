# Verified — Bug #4: W875RX1 mis-labelled fiscal / redundant with DSPIC96

## Verdict
PARTIALLY CONFIRMED — the *mislabel* claim is correct (W875RX1 is not a fiscal-policy
variable by any standard FRED definition); the *redundancy* claim is correct only on
levels, and is **refuted** on the actual transformation used (`pch`), where the two
series carry meaningfully different information precisely during fiscal-transfer
events that the thesis cares about.

## Evidence

### W875RX1 in fiscal spec
From `Spec_US_fiscal.xlsx`, row 34:

```
Model SeriesID  SeriesName                                                Frequency  Block1-Global  Block2-Soft  Block3-Real  Block4-Labor  Transformation  Units                Category
    1 W875RX1   Real personal income excluding current transfer receipts  m          1              0            1            0             pch             Chained $, Billions  Fiscal
```

- Frequency: m (monthly)
- Transformation: `pch` (% change month-over-month)
- Blocks loaded: Global + Real
- Category: **Fiscal** (this is the disputed labelling)
- Model status: `1` (active — included in estimation)

### DSPIC96 in baseline spec
From `Spec_US_new.xlsx`, row 11:

```
Model SeriesID  SeriesName       Frequency  Block1-Global  Block2-Soft  Block3-Real  Block4-Labor  Transformation  Units                Category
    1 DSPIC96   Personal Income  m          1              0            1            0             pch             Chained $, Billions  National Accounts
```

- Same frequency, same transformation, same block structure as W875RX1.
- Category: **National Accounts**.
- Model status: `1` (active).
- Note: The thesis labels DSPIC96 simply as "Personal Income" in the `SeriesName`
  column, which is sloppy — on FRED, `DSPIC96` is *Real Disposable Personal Income*
  (i.e. personal income net of personal current taxes). This is a separate labelling
  bug worth flagging (it is the same row text in both specs).

### Series membership cross-check
Programmatic check of `SeriesID` columns across the two specs:

| Series | In `Spec_US_new.xlsx` (baseline) | In `Spec_US_fiscal.xlsx` (fiscal) |
|---|---|---|
| W875RX1 | No | Yes |
| DSPIC96 | Yes | Yes |
| GCEC1   | No | Yes |
| MTSDS133FMS | No | Yes |

Fiscal-only additions (set difference): `{W875RX1, MTSDS133FMS, GCEC1}` — exactly the
three "fiscal" variables. Baseline has no series that fiscal does not have.

So W875RX1 is **a fiscal-only addition**; DSPIC96 is **in both specs** (so the
baseline already had it before W875RX1 was added).

### FRED semantics

Restated in the spirit of the audit claim, then verified algebraically against the
column data:

- **W875RX1** = *Real personal income excluding current transfer receipts*. Personal
  income strips out government social-benefit transfers (Social Security, Medicare,
  Medicaid, unemployment insurance, SNAP, stimulus payments to individuals, etc.).
  Constructed primarily from wages, proprietors' income, rental income, dividends,
  and interest — i.e. **market income**, not fiscal-policy income.
- **DSPIC96** = *Real Disposable Personal Income*. Total personal income (which
  *includes* transfer receipts) **minus** personal current taxes, then deflated.
- Algebraic relation (in real terms, schematically):
  - `DSPIC96 ≈ (W875RX1) + (real transfer receipts) − (real personal taxes)`
  - Equivalently: `W875RX1 ≈ DSPIC96 − transfers + taxes`.

The "ex-transfers" construction of W875RX1 is precisely what **removes** the direct
imprint of fiscal policy on household income. From a fiscal-policy standpoint, a
shock to transfers (e.g. CARES Act stimulus checks, expanded UI) shows up in DSPIC96
(via the "+ transfers" term) and is absent from W875RX1 by construction. So W875RX1
is, if anything, the *cleaner business-cycle / labour-and-capital-income* signal — it
is what is typically used as a transfer-cleaned activity proxy, not a fiscal-policy
indicator.

### Empirical correlation
Computed on the 2024-10-04 vintage (`data/US_fiscal/2024-10-04.xlsx`), 476 aligned
monthly observations from 1985-01 to 2024-08:

| Transformation | Sample | Pearson r |
|---|---|---|
| Levels | full (1985–2024, n=476) | **0.9928** |
| `pch` (m/m %) | full | **0.0921** |
| YoY (12m %) | full | **0.3327** |
| Log-diff m/m | full | 0.0995 |
| Levels | post-2000 (n=296) | 0.9766 |
| `pch` (m/m %) | post-2000 | -0.0030 |
| YoY (12m %) | post-2000 | 0.1870 |
| `pch` (m/m %) | ex-COVID (2020-01..2021-06 dropped, n=458) | **0.7514** |
| YoY (12m %) | ex-COVID | 0.7477 |

The largest absolute m/m divergences are concentrated in transfer-policy events:

| Month | \|Δpch W875RX1 − Δpch DSPIC96\| |
|---|---|
| 2021-03 (ARP stimulus) | 0.220 |
| 2020-04 (CARES stimulus) | 0.209 |
| 2021-04 (post-stimulus reversion) | 0.160 |
| 2021-01 (Dec-2020 stimulus) | 0.110 |
| 2021-02 | 0.084 |
| 2020-05 | 0.074 |
| 2008-05 (ESA-2008 rebate) | 0.053 |

In April 2020: DSPIC96 jumped +14.8% m/m (massive stimulus payment) while W875RX1
fell −6.1% m/m (collapsing market income) — they moved in *opposite directions* by
~21 percentage points.

## Magnitude assessment
- **On levels** (r = 0.99): the audit's >0.95 threshold is met and exceeded. Two
  near-cointegrated trending series share virtually the same long-run path.
- **On the transformation actually used in the spec (`pch`)**: r = 0.09 full
  sample, ~0.75 ex-COVID, ~0.00 post-2000 full sample. **The audit's redundancy
  argument breaks down once you move to the transformation the model actually
  consumes.** The DFM operates on transformed series, not levels, so the relevant
  correlation for redundancy assessment is the `pch` one, not the level one.
- **Absorbed by the idiosyncratic AR(1)?** On full-sample `pch`, the two series
  share <1% of variance, so DSPIC96 cannot mechanically "absorb" W875RX1's signal
  via the global factor — most of W875RX1's `pch` variation has to be loaded on
  either its own idiosyncratic component or remain unexplained. The audit's
  observation that W875RX1's Fig A7 contribution is small (~0.03) is therefore
  consistent with the DFM finding it informative but not dominant, *not* with it
  being redundant.
- **Is calling W875RX1 a "fiscal variable" defensible?** No. By construction
  W875RX1 *removes* transfer receipts, which are the primary household-side
  channel of fiscal policy. Standard usage (BEA, FRED, NIPA glossary) describes
  W875RX1 as the transfer-cleaned activity indicator. If anything, it belongs in
  `National Accounts` next to DSPIC96, or in `Retail and Consumption` as a
  consumer-spending leading indicator. Categorising it as `Fiscal` is a
  taxonomic error, even if the variable itself is empirically useful.

## Notes / caveats
The audit conflates two distinct claims; they should be reported separately:

1. **Mislabel claim (W875RX1 is not fiscal)** — **CONFIRMED**. The FRED/NIPA
   definition is unambiguous: W875RX1 is *market* income, deliberately stripped of
   transfers. Calling it a fiscal-policy variable is the opposite of what the series
   measures. Fix: re-categorise to `National Accounts` (or move to baseline spec
   altogether — see below), and correct the misleading `SeriesName`/`Category`
   pairing.

2. **Redundancy claim (W875RX1 ≈ DSPIC96, drop it)** — **REFUTED on the
   transformation used.** Level correlation of 0.99 is real but irrelevant to a DFM
   on `pch` data. Month-over-month, W875RX1 and DSPIC96 carry materially different
   information whenever transfers move (COVID, 2008 rebate, ARP), which is *exactly*
   the regime where a fiscal-augmented model should outperform. The two series are
   complementary, not substitutes: DSPIC96 captures household *cash-flow* income
   (including fiscal injections), W875RX1 captures household *market* income (the
   business-cycle signal that fiscal policy is responding to). The thesis's
   probable intent in adding W875RX1 was to give the model a transfer-cleaned
   activity reading *alongside* DSPIC96, so it can distinguish "real economy
   slowed" from "real economy slowed but disposable income propped up by stimulus".
   That is methodologically defensible.

Additional issue surfaced during verification:

- `DSPIC96`'s `SeriesName` in both specs is just "Personal Income". That is wrong —
  DSPIC96 is *Real Disposable Personal Income*. The series ID, units, and
  transformation are correct, but the human-readable name conflates DSPIC96 with
  PI (FRED `PI`) and is itself an audit-worthy labelling bug. The "Personal Income"
  series ID on FRED is `PI` (nominal) or `RPI` (real); neither is in either spec.

### Recommended action (revised relative to audit)
- **Keep** W875RX1 in the fiscal spec for empirical reasons (it carries
  non-redundant `pch` signal, especially around fiscal-transfer episodes which is
  what the fiscal extension exists to capture).
- **Recategorise** its `Category` field from `Fiscal` to `National Accounts` (or
  add a `Notes` column flagging "transfer-cleaned activity proxy, included to
  separate market-income from transfer-income channels"), so the taxonomy does
  not claim that an ex-transfers series measures fiscal policy.
- **Fix** the DSPIC96 `SeriesName` to "Real Disposable Personal Income" in both
  specs.

## Commands run

```python
# 1. Read fiscal spec
import pandas as pd
df = pd.read_excel(r'Spec_US_fiscal.xlsx')
df[df['SeriesID']=='W875RX1']
df[df['SeriesID']=='DSPIC96']

# 2. Read baseline spec
base = pd.read_excel(r'Spec_US_new.xlsx')
base[base['SeriesID']=='DSPIC96']

# 3. Membership cross-check
'W875RX1' in fiscal['SeriesID'].values        # True
'W875RX1' in base['SeriesID'].values          # False
'DSPIC96' in fiscal['SeriesID'].values        # True
'DSPIC96' in base['SeriesID'].values          # True
set(fiscal['SeriesID']) - set(base['SeriesID'])  # {'W875RX1','MTSDS133FMS','GCEC1'}

# 4. Empirical correlations on 2024-10-04 vintage
df = pd.read_excel(r'data/US_fiscal/2024-10-04.xlsx')
df['Date'] = pd.to_datetime(df['Date']); df = df.set_index('Date').sort_index()
joined = pd.concat([df['W875RX1'], df['DSPIC96']], axis=1).dropna()
joined['W875RX1'].corr(joined['DSPIC96'])                  # 0.9928 (levels)
joined.pct_change().dropna().corr().iloc[0,1]              # 0.0921 (pch m/m)
joined.pct_change(12).dropna().corr().iloc[0,1]            # 0.3327 (YoY)
# subsamples
post = joined[joined.index >= '2000-01-01']                # n=296
exc  = joined[(joined.index<'2020-01-01') | (joined.index>='2021-07-01')]  # ex-COVID
```
