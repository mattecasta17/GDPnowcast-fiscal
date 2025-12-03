import os
import time
from pathlib import Path
from datetime import datetime, date
from dateutil.rrule import rrule, WEEKLY, FR
import pandas as pd
import numpy as np
from fredapi import Fred

# ---------- USER SETTINGS ----------
OUTPUT_DIR    = Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\data\US_fiscal2")
DATA_START    = pd.Timestamp("1985-01-01")

VINTAGE_START = date(2016, 12, 9)
VINTAGE_END   = date(2025, 7, 25)

PAUSE_BETWEEN_CALLS = 1.1
MAX_RETRIES          = 6
BACKOFF_START_SEC    = 2.0
# -----------------------------------

TARGET_SERIES = ["GCEC1", "MTSDS133FMS", "W875RX1"]

def get_fred():
    api_key = os.environ.get("FRED_API_KEY") or "64b47ef802cce7ec9c8b65d476e9a8ea"
    return Fred(api_key=api_key)

def fridays_between(start_d: date, end_d: date):
    return [d.date() for d in rrule(freq=WEEKLY, byweekday=FR,
                                    dtstart=datetime(start_d.year, start_d.month, start_d.day),
                                    until=datetime(end_d.year, end_d.month, end_d.day))]

def monthly_index(start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start=start_ts, end=end_ts, freq="MS")

def fetch_fred_monthly_asof(fred: Fred, fred_id: str, vintage_str: str, freq="M") -> pd.Series:
    wait = BACKOFF_START_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            s = fred.get_series(fred_id, realtime_start=vintage_str, realtime_end=vintage_str)
            if s is None or s.empty:
                return pd.Series(dtype=float)
            s = s.to_frame("value")
            s.index = pd.to_datetime(s.index)

            if freq == "Q":
                # Mantieni solo una data per trimestre: quella ufficiale del trimestre (es. 1985-03-31)
                s.index = s.index.to_period("Q").to_timestamp(how="start")
            else:
                s = s.resample("MS").last()

            return s["value"]
        except Exception as e:
            msg = str(e)
            if "Too Many Requests" in msg or "Exceeded Rate Limit" in msg or "timed out" in msg or "connection" in msg.lower():
                if attempt < MAX_RETRIES:
                    print(f"Rate limited on {fred_id} (attempt {attempt}/{MAX_RETRIES}). Waiting {wait:.1f}s…")
                    time.sleep(wait); wait *= 2; continue
            print(f"⚠️ Errore scaricando {fred_id}: {e}")
            return pd.Series(dtype=float)
        finally:
            time.sleep(PAUSE_BETWEEN_CALLS)

def main():
    fred = get_fred()
    vintage_dates = fridays_between(VINTAGE_START, VINTAGE_END)

    for vd in vintage_dates:
        fname = f"{vd.isoformat()}.xlsx"
        fpath = OUTPUT_DIR / fname
        if not fpath.exists():
            print(f"❌ File non trovato: {fpath}")
            continue

        print(f"\n🔄 Aggiornamento vintage {vd.isoformat()} ...")
        df = pd.read_excel(fpath)

        if "Date" not in df.columns:
            print(f"⚠️ Nessuna colonna 'Date' in {fpath}, salto.")
            continue

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

        vintage_str = vd.strftime("%Y-%m-%d")
        for var in TARGET_SERIES:
            freq = "Q" if var == "GCEC1" else "M"
            print(f"  ➜ Aggiornamento {var}...")
            s = fetch_fred_monthly_asof(fred, var, vintage_str, freq=freq)
            s = s.loc[DATA_START:vd]

            if s.empty:
                print(f"    ⚠️ Nessun dato per {var}")
                continue
            # 🔄 Sposta GCEC1 di due mesi avanti, così finisce sull’ultimo mese del trimestre
            if var == "GCEC1":
                s = s.shift(2, freq="MS")

            if var in df.columns:
                df[var] = df[var].combine_first(s).copy()
            else:
                df[var] = s.copy()

            print(f"    ✅ Inseriti {s.dropna().shape[0]} punti per {var}")

        # Reimposta l'indice come colonna e salva
        df = df.reset_index()
        df.to_excel(fpath, index=False)
        print(f"💾 Salvato {fname}")

    print("\n✅ COMPLETATO con successo!")


if __name__ == "__main__":
    main()



