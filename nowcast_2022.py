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

#------------------------------------------------- True GDP values for 2022
gdp_adv_estimate = {
    "2022q1": -1.4,
    "2022q2": -0.9,
    "2022q3": 2.6,
    "2022q4": 2.9
}

#------------------------------------------------- Vintages per quarter for 2022
vintages_dict_2022 = {
    "2022q1": [
        "2021-12-03", "2021-12-10", "2021-12-17", "2021-12-24", "2021-12-31",
        "2022-01-07", "2022-01-14", "2022-01-21", "2022-01-28", "2022-02-04",
        "2022-02-11", "2022-02-18", "2022-02-25", "2022-03-04", "2022-03-11",
        "2022-03-18", "2022-03-25", "2022-04-01", "2022-04-08", "2022-04-15",
        "2022-04-22", "2022-04-29"
    ],
    "2022q2": [
        "2022-03-04", "2022-03-11", "2022-03-18", "2022-03-25", "2022-04-01",
        "2022-04-08", "2022-04-15", "2022-04-22", "2022-04-29", "2022-05-06",
        "2022-05-13", "2022-05-20", "2022-05-27", "2022-06-03", "2022-06-10",
        "2022-06-17", "2022-06-24", "2022-07-01", "2022-07-08", "2022-07-15",
        "2022-07-22", "2022-07-29"
    ],
    "2022q3": [
        "2022-06-03", "2022-06-10", "2022-06-17", "2022-06-24", "2022-07-01",
        "2022-07-08", "2022-07-15", "2022-07-22", "2022-07-29", "2022-08-05",
        "2022-08-12", "2022-08-19", "2022-08-26", "2022-09-02", "2022-09-09",
        "2022-09-16", "2022-09-23", "2022-09-30", "2022-10-07", "2022-10-14",
        "2022-10-21", "2022-10-28"
    ],
    "2022q4": [
        "2022-09-02", "2022-09-09", "2022-09-16", "2022-09-23", "2022-09-30",
        "2022-10-07", "2022-10-14", "2022-10-21", "2022-10-28", "2022-11-04",
        "2022-11-11", "2022-11-18", "2022-11-25", "2022-12-02", "2022-12-09",
        "2022-12-16", "2022-12-23", "2022-12-30", "2023-01-06", "2023-01-13",
        "2023-01-20", "2023-01-27"
    ]
}

#------------------------------------------------- Parameter configuration (nuova logica prev/curr)
param_map_2022 = {
    "2022q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20211001.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20220103.pickle"),
        "switch_date": "2022-01-01"
    },
    "2022q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20220103.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20220401.pickle"),
        "switch_date": "2022-04-01"
    },
    "2022q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20220401.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20220701.pickle"),
        "switch_date": "2022-07-01"
    },
    "2022q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20220701.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20221003.pickle"),
        "switch_date": "2022-10-01"
    }
}

#------------------------------------------------- Cache pickle loader
param_cache = {}

def load_pickle_cached(path):
    """Carica il file pickle solo la prima volta, poi usa la cache."""
    if path not in param_cache:
        with open(path, 'rb') as h:
            param_cache[path] = pickle.load(h)['Res']
    return param_cache[path]

#------------------------------------------------- Loop over quarters for 2022
for period, vintages in vintages_dict_2022.items():
    print(f"Processing {period} ...")

    cfg = param_map_2022[period]
    switch_dt = pd.to_datetime(cfg["switch_date"])

    # Usa la cache
    Res_prev = load_pickle_cached(cfg["prev"])
    Res_curr = load_pickle_cached(cfg["curr"])

    gdp_actual = gdp_adv_estimate[period]
    news_output_file = f"news_Q/news_{period[:4]}_{period[4:]}.xlsx"

    results_list = []
    news_tables_dict = {}

    for i in range(1, len(vintages)):
        vintage_old = vintages[i-1]
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
    metrics.to_csv(f"metrics_Q/metrics_{period[:4]}_{period[4:]}.csv", index=False)
    print(f"Saved metrics_Q/metrics_{period[:4]}_{period[4:]}.csv")

    # Save news
    with pd.ExcelWriter(news_output_file) as writer:
        for vintage, df_news in news_tables_dict.items():
            sheet_name = vintage.replace("2022-", "").replace("2023-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")
