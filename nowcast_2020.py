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

#------------------------------------------------- True GDP values for 2020
gdp_adv_estimate = {
    "2020q1": -4.8,
    "2020q2": -32.9,
    "2020q3": 33.1,
    "2020q4": 4.0
}

#------------------------------------------------- Vintages per quarter for 2020
vintages_dict_2020 = {
    "2020q1": [
        "2019-12-06", "2019-12-13", "2019-12-20", "2019-12-27",
        "2020-01-03", "2020-01-10", "2020-01-17", "2020-01-24", "2020-01-31",
        "2020-02-07", "2020-02-14", "2020-02-21", "2020-02-28", "2020-03-06",
        "2020-03-13", "2020-03-20", "2020-03-27", "2020-04-03", "2020-04-10",
        "2020-04-17", "2020-04-24", "2020-05-01"
    ],
    "2020q2": [
        "2020-03-06", "2020-03-13", "2020-03-20", "2020-03-27", "2020-04-03",
        "2020-04-10", "2020-04-17", "2020-04-24", "2020-05-01", "2020-05-08",
        "2020-05-15", "2020-05-22", "2020-05-29", "2020-06-05", "2020-06-12",
        "2020-06-19", "2020-06-26", "2020-07-03", "2020-07-10", "2020-07-17",
        "2020-07-24", "2020-07-31"
    ],
    "2020q3": [
        "2020-06-05", "2020-06-12", "2020-06-19", "2020-06-26", "2020-07-03",
        "2020-07-10", "2020-07-17", "2020-07-24", "2020-07-31", "2020-08-07",
        "2020-08-14", "2020-08-21", "2020-08-28", "2020-09-04", "2020-09-11",
        "2020-09-18", "2020-09-25", "2020-10-02", "2020-10-09", "2020-10-16",
        "2020-10-23", "2020-10-30"
    ],
    "2020q4": [
        "2020-09-04", "2020-09-11", "2020-09-18", "2020-09-25", "2020-10-02",
        "2020-10-09", "2020-10-16", "2020-10-23", "2020-10-30", "2020-11-06",
        "2020-11-13", "2020-11-20", "2020-11-27", "2020-12-04", "2020-12-11",
        "2020-12-18", "2020-12-25", "2021-01-01", "2021-01-08", "2021-01-15",
        "2021-01-22", "2021-01-29"
    ]
}

#------------------------------------------------- Parameter configuration
param_map_2020 = {
    "2020q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20191001.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20200102.pickle"),
        "switch_date": "2020-01-01"
    },
    "2020q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20200102.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20200401.pickle"),
        "switch_date": "2020-04-01"
    },
    "2020q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20200401.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20200701.pickle"),
        "switch_date": "2020-07-01"
    },
    "2020q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20200701.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20201001.pickle"),
        "switch_date": "2020-10-01"
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

#------------------------------------------------- Loop over quarters for 2020
for period, vintages in vintages_dict_2020.items():
    print(f"Processing {period} ...")

    cfg = param_map_2020[period]
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
            sheet_name = vintage.replace("2020-", "").replace("2021-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")


