#------------------------------------------------- Libraries
from Functions.load_data import load_data
from Functions.load_spec import load_spec
from Functions.update_Nowcast2 import update_nowcast2
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

#------------------------------------------------- Config
series = 'GDPC1'
Spec   = load_spec('Spec_US_fiscal.xlsx')

# Ensure output directories
os.makedirs("nowcast_Q_fiscal", exist_ok=True)
os.makedirs("metrics_Q_fiscal", exist_ok=True)
os.makedirs("news_Q_fiscal", exist_ok=True)

#------------------------------------------------- True GDP values for 2024
gdp_adv_estimate = {
    "2024q1": 1.6,
    "2024q2": 2.8,
    "2024q3": 2.8,
    "2024q4": 2.3
}

#------------------------------------------------- Vintages per quarter for 2024
vintages_dict_2024 = {
    "2024q1": [
        "2023-12-01", "2023-12-08", "2023-12-15", "2023-12-22", "2023-12-29",
        "2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26", "2024-02-02",
        "2024-02-09", "2024-02-16", "2024-02-23", "2024-03-01", "2024-03-08",
        "2024-03-15", "2024-03-22", "2024-03-29", "2024-04-05", "2024-04-12",
        "2024-04-19", "2024-04-26"
    ],
    "2024q2": [
        "2024-03-01", "2024-03-08", "2024-03-15", "2024-03-22", "2024-03-29",
        "2024-04-05", "2024-04-12", "2024-04-19", "2024-04-26", "2024-05-03",
        "2024-05-10", "2024-05-17", "2024-05-24", "2024-05-31", "2024-06-07",
        "2024-06-14", "2024-06-21", "2024-06-28", "2024-07-05", "2024-07-12",
        "2024-07-19", "2024-07-26"
    ],
    "2024q3": [
        "2024-06-07", "2024-06-14", "2024-06-21", "2024-06-28",
        "2024-07-05", "2024-07-12", "2024-07-19", "2024-07-26", "2024-08-02",
        "2024-08-09", "2024-08-16", "2024-08-23", "2024-08-30", "2024-09-06",
        "2024-09-13", "2024-09-20", "2024-09-27", "2024-10-04", "2024-10-11",
        "2024-10-18", "2024-10-25", "2024-11-01"
    ],
    "2024q4": [
        "2024-08-30", "2024-09-06", "2024-09-13", "2024-09-20", "2024-09-27",
        "2024-10-04", "2024-10-11", "2024-10-18", "2024-10-25", "2024-11-01",
        "2024-11-08", "2024-11-15", "2024-11-22", "2024-11-29", "2024-12-06",
        "2024-12-13", "2024-12-20", "2024-12-27", "2025-01-03", "2025-01-10",
        "2025-01-17", "2025-01-31"
    ]
}

#------------------------------------------------- Parameter configuration (switch logic)
param_map_2024 = {
    "2024q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20231002.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20240102.pickle"),
        "switch_date": "2024-01-01"
    },
    "2024q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20240102.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20240401.pickle"),
        "switch_date": "2024-04-01"
    },
    "2024q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20240401.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20240701.pickle"),
        "switch_date": "2024-07-01"
    },
    "2024q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20240701.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param_fiscal\ResDFM_fiscal_20241001.pickle"),
        "switch_date": "2024-10-01"
    }
}

#------------------------------------------------- Cache pickle loader
param_cache = {}

def load_pickle_cached(path):
    """Carica il file pickle una sola volta e lo riutilizza dalla cache."""
    if path not in param_cache:
        with open(path, 'rb') as h:
            param_cache[path] = pickle.load(h)['Res']
    return param_cache[path]

#------------------------------------------------- Loop over quarters for 2024
for period, vintages in vintages_dict_2024.items():
    print(f"Processing {period} ...")

    cfg = param_map_2024[period]
    switch_dt = pd.to_datetime(cfg["switch_date"])

    # Usa cache
    Res_prev = load_pickle_cached(cfg["prev"])
    Res_curr = load_pickle_cached(cfg["curr"])

    gdp_actual = gdp_adv_estimate[period]
    news_output_file = f"news_Q_fiscal/news_{period[:4]}_{period[4:]}_fiscal.xlsx"

    results_list = []
    news_tables_dict = {}

    for i in range(1, len(vintages)):
        vintage_old = vintages[i-1]
        vintage_new = vintages[i]

        try:
            v_new_dt = pd.to_datetime(vintage_new)
            Res = Res_prev if v_new_dt < switch_dt else Res_curr

            datafile_old = os.path.join('data', 'US_fiscal', vintage_old + '.xlsx')
            datafile_new = os.path.join('data', 'US_fiscal', vintage_new + '.xlsx')
            X_old, _, _ = load_data(datafile_old, Spec)
            X_new, Time, _ = load_data(datafile_new, Spec)

            results = update_nowcast2(
                X_old, X_new, Time, Spec, Res,
                series, period, vintage_old, vintage_new,
                display=False
            )

            y_old = results["y_old"][0]
            y_new = results["y_new"][0]
            error = gdp_actual - y_new
            abs_error = abs(error)
            perc_error = error / gdp_actual if gdp_actual != 0 else np.nan
            variance_so_far = np.var([y_old, y_new])

            results_list.append({
                "vintage": vintage_new,
                "y_old": y_old,
                "y_new": y_new,
                "error": error,
                "abs_error": abs_error,
                "perc_error": perc_error,
                "impact_revisions": results["impact_revisions"][0],
                "impact_releases": np.nansum(results["impact_releases"]),
                "variance_so_far": variance_so_far,
                "params_used": "prev" if v_new_dt < switch_dt else "curr"
            })

            news_tables_dict[vintage_new] = results["news_table"]

        except Exception as e:
            print(f"Skipping {vintage_new}: {e}")
            continue

    # Save results
    df_results = pd.DataFrame(results_list)
    df_results.to_csv(f"nowcast_Q_fiscal/nowcast_{period[:4]}_{period[4:]}_fiscal.csv", index=False)
    print(f"Saved nowcast_Q/nowcast_{period[:4]}_{period[4:]}_fiscal.csv")

    # Compute metrics
    RMSE = np.sqrt(np.mean(df_results["error"]**2))
    MAE  = np.mean(df_results["abs_error"])
    Bias = np.mean(df_results["error"])
    MPE  = np.mean(df_results["perc_error"]) * 100

    metrics = pd.DataFrame([{
        "quarter": period.upper(),
        "RMSE": RMSE,
        "MAE": MAE,
        "Bias": Bias,
        "MPE": MPE
    }])
    metrics.to_csv(f"metrics_Q_fiscal/metrics_{period[:4]}_{period[4:]}_fiscal.csv", index=False)
    print(f"Saved metrics_Q_fiscal/metrics_{period[:4]}_{period[4:]}_fiscal.csv")

    # Save news
    with pd.ExcelWriter(news_output_file) as writer:
        for vintage, df_news in news_tables_dict.items():
            sheet_name = vintage.replace("2024-", "").replace("2025-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")