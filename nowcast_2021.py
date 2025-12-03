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

#------------------------------------------------- True GDP values for 2021
gdp_adv_estimate = {
    "2021q1": 6.4,
    "2021q2": 6.5,
    "2021q3": 2.0,
    "2021q4": 6.9
}

#------------------------------------------------- Vintages per quarter for 2021
vintages_dict_2021 = {
    "2021q1": [
        "2020-12-04", "2020-12-11", "2020-12-18", "2020-12-25", "2021-01-01",
        "2021-01-08", "2021-01-15", "2021-01-22", "2021-01-29", "2021-02-05",
        "2021-02-12", "2021-02-19", "2021-02-26", "2021-03-05", "2021-03-12",
        "2021-03-19", "2021-03-26", "2021-04-02", "2021-04-09", "2021-04-16",
        "2021-04-23", "2021-04-30"
    ],
    "2021q2": [
        "2021-03-05", "2021-03-12", "2021-03-19", "2021-03-26", "2021-04-02",
        "2021-04-09", "2021-04-16", "2021-04-23", "2021-04-30", "2021-05-07",
        "2021-05-14", "2021-05-21", "2021-05-28", "2021-06-04", "2021-06-11",
        "2021-06-18", "2021-06-25", "2021-07-02", "2021-07-09", "2021-07-16",
        "2021-07-23", "2021-07-30"
    ],
    "2021q3": [
        "2021-06-04", "2021-06-11", "2021-06-18", "2021-06-25", "2021-07-02",
        "2021-07-09", "2021-07-16", "2021-07-23", "2021-07-30", "2021-08-06",
        "2021-08-13", "2021-08-20", "2021-08-27", "2021-09-03", "2021-09-10",
        "2021-09-17", "2021-09-24", "2021-10-01", "2021-10-08", "2021-10-15",
        "2021-10-22", "2021-10-29"
    ],
    "2021q4": [
        "2021-09-03", "2021-09-10", "2021-09-17", "2021-09-24", "2021-10-01",
        "2021-10-08", "2021-10-15", "2021-10-22", "2021-10-29", "2021-11-05",
        "2021-11-12", "2021-11-19", "2021-11-26", "2021-12-03", "2021-12-10",
        "2021-12-17", "2021-12-24", "2021-12-31", "2022-01-07", "2022-01-14",
        "2022-01-21", "2022-01-28"
    ]
}

#------------------------------------------------- Parameter configuration
param_map_2021 = {
    "2021q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20201001.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20210101.pickle"),
        "switch_date": "2021-01-01"
    },
    "2021q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20210101.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20210401.pickle"),
        "switch_date": "2021-04-01"
    },
    "2021q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20210401.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20210701.pickle"),
        "switch_date": "2021-07-01"
    },
    "2021q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20210701.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20211001.pickle"),
        "switch_date": "2021-10-01"
    }
}

#------------------------------------------------- Cache pickle loader (ottimizzazione)
param_cache = {}

def load_pickle_cached(path):
    """Carica il file pickle solo la prima volta, poi usa la cache."""
    if path not in param_cache:
        with open(path, 'rb') as h:
            param_cache[path] = pickle.load(h)['Res']
    return param_cache[path]

#------------------------------------------------- Loop over quarters for 2021
for period, vintages in vintages_dict_2021.items():
    print(f"Processing {period} ...")

    cfg = param_map_2021[period]
    switch_dt = pd.to_datetime(cfg["switch_date"])

    # Usa la cache per i file pickle
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
            sheet_name = vintage.replace("2021-", "").replace("2022-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")

