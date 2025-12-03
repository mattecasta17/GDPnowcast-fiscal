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
Spec   = load_spec('Spec_US_new.xlsx')

# Ensure output directories
os.makedirs("nowcast_Q", exist_ok=True)
os.makedirs("metrics_Q", exist_ok=True)
os.makedirs("news_Q", exist_ok=True)

#------------------------------------------------- True GDP values for 2025
gdp_adv_estimate = {
    "2025q1": -0.3,
    "2025q2": 3.0
}

#------------------------------------------------- Vintages per quarter for 2025
vintages_dict_2025 = {
    "2025q1": [
        "2024-11-08", "2024-11-15", "2024-11-22", "2024-11-29",
        "2024-12-06", "2024-12-13", "2024-12-20", "2024-12-27", "2025-01-03",
        "2025-01-10", "2025-01-17", "2025-01-24", "2025-01-31", "2025-02-07",
        "2025-02-14", "2025-02-21", "2025-02-28", "2025-03-07", "2025-03-14",
        "2025-03-21", "2025-04-25", "2025-05-02"
    ],
    "2025q2": [
        "2025-02-28", "2025-03-07", "2025-03-14", "2025-03-21", "2025-03-28",
        "2025-04-04", "2025-04-11", "2025-04-18", "2025-04-25", "2025-05-02",
        "2025-05-09", "2025-05-16", "2025-05-23", "2025-05-30", "2025-06-06",
        "2025-06-13", "2025-06-20", "2025-06-27", "2025-07-04", "2025-07-11",
        "2025-07-18", "2025-07-25",
    ]
}

#------------------------------------------------- Parameter configuration (switch logic)
param_map_2025 = {
    "2025q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20241001.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20250102.pickle"),
        "switch_date": "2025-01-01"
    },
    "2025q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20250102.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20250401.pickle"),
        "switch_date": "2025-04-01"
    }
}

#------------------------------------------------- Cache pickle loader
param_cache = {}

def load_pickle_cached(path):
    """Carica il file pickle solo la prima volta e lo riutilizza dalla cache."""
    if path not in param_cache:
        with open(path, 'rb') as h:
            param_cache[path] = pickle.load(h)['Res']
    return param_cache[path]

#------------------------------------------------- Loop over quarters for 2025
for period, vintages in vintages_dict_2025.items():
    print(f"Processing {period} ...")

    cfg = param_map_2025[period]
    switch_dt = pd.to_datetime(cfg["switch_date"])

    # Carica i pickle una sola volta
    Res_prev = load_pickle_cached(cfg["prev"])
    Res_curr = load_pickle_cached(cfg["curr"])

    gdp_actual = gdp_adv_estimate[period]
    news_output_file = f"news_Q/news_{period[:4]}_{period[4:]}.xlsx"

    results_list = []
    news_tables_dict = {}

    for i in range(1, len(vintages)):
        vintage_old = vintages[i - 1]
        vintage_new = vintages[i]

        try:
            v_new_dt = pd.to_datetime(vintage_new)
            Res = Res_prev if v_new_dt < switch_dt else Res_curr

            datafile_old = os.path.join('data', 'US_new', vintage_old + '.xlsx')
            datafile_new = os.path.join('data', 'US_new', vintage_new + '.xlsx')
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
    df_results.to_csv(f"nowcast_Q/nowcast_{period[:4]}_{period[4:]}.csv", index=False)
    print(f"Saved nowcast_Q/nowcast_{period[:4]}_{period[4:]}.csv")

    # Compute metrics
    RMSE = np.sqrt(np.mean(df_results["error"] ** 2))
    MAE = np.mean(df_results["abs_error"])
    Bias = np.mean(df_results["error"])
    MPE = np.mean(df_results["perc_error"]) * 100

    metrics = pd.DataFrame([{
        "quarter": period.upper(),
        "RMSE": RMSE,
        "MAE": MAE,
        "Bias": Bias,
        "MPE": MPE
    }])
    metrics.to_csv(f"metrics_Q/metrics_{period[:4]}_{period[4:]}.csv", index=False)
    print(f"Saved metrics_Q/metrics_{period[:4]}_{period[4:]}.csv")

    # Save news
    with pd.ExcelWriter(news_output_file) as writer:
        for vintage, df_news in news_tables_dict.items():
            sheet_name = vintage.replace("2025-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")
