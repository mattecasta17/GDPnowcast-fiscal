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

#------------------------------------------------- True GDP values for 2017
gdp_adv_estimate = {
    "2017q1": 0.7,
    "2017q2": 2.6,
    "2017q3": 3.0,
    "2017q4": 2.6
}

#------------------------------------------------- Vintages per quarter
vintages_dict = {
    "2017q1": [
        "2016-12-02","2016-12-09","2016-12-16","2016-12-23","2016-12-30",
        "2017-01-06","2017-01-13","2017-01-20","2017-01-27",
        "2017-02-03","2017-02-10","2017-02-17","2017-02-24",
        "2017-03-03","2017-03-10","2017-03-17","2017-03-24","2017-03-31",
        "2017-04-07","2017-04-14","2017-04-21","2017-04-28"
    ],
    "2017q2": [
        "2017-03-03","2017-03-10","2017-03-17","2017-03-24","2017-03-31",
        "2017-04-07","2017-04-14","2017-04-21","2017-04-28",
        "2017-05-05","2017-05-12","2017-05-19","2017-05-26",
        "2017-06-02","2017-06-09","2017-06-16","2017-06-23","2017-06-30",
        "2017-07-07","2017-07-14","2017-07-21","2017-07-28"
    ],
    "2017q3": [
        "2017-06-02","2017-06-09","2017-06-16","2017-06-23","2017-06-30",
        "2017-07-07","2017-07-14","2017-07-21","2017-07-28",
        "2017-08-04","2017-08-11","2017-08-18","2017-08-25",
        "2017-09-01","2017-09-08","2017-09-15","2017-09-22","2017-09-29",
        "2017-10-06","2017-10-13","2017-10-20","2017-10-27"
    ],
    "2017q4": [
        "2017-09-01","2017-09-08","2017-09-15","2017-09-22","2017-09-29",
        "2017-10-06","2017-10-13","2017-10-20","2017-10-27",
        "2017-11-03","2017-11-10","2017-11-17","2017-11-24",
        "2017-12-01","2017-12-08","2017-12-15","2017-12-22","2017-12-29",
        "2018-01-05","2018-01-12","2018-01-19","2018-01-26"
    ]
}

#------------------------------------------------- Parametri per logica "fixed within quarter, re-estimate at quarter start"
# Per ogni trimestre: usa 'prev' fino al giorno prima di switch_date; da switch_date in poi usa 'curr'
param_map_2017 = {
    "2017q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20161003.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20170103.pickle"),
        "switch_date": "2017-01-01"
    },
    "2017q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20170103.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20170403.pickle"),
        "switch_date": "2017-04-01"
    },
    "2017q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20170403.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20170703.pickle"),
        "switch_date": "2017-07-01"
    },
    "2017q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20170703.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20171002.pickle"),
        "switch_date": "2017-10-01"
    }
}

# Cache per non riaprire i pickle
_loaded_params = {}

def load_res_cached(path_obj: Path):
    key = str(path_obj)
    if key not in _loaded_params:
        with open(path_obj, 'rb') as handle:
            _loaded_params[key] = pickle.load(handle)['Res']
    return _loaded_params[key]

def check_vintage_file(vintage, folder):
    file_path = os.path.join(folder, vintage + '.xlsx')
    if os.path.exists(file_path):
        print(f"Loading file from {folder}: {file_path}")
        return file_path
    else:
        print(f"File not found in {folder}: {file_path}")
        return None

#------------------------------------------------- Loop over quarters
for period, vintages in vintages_dict.items():
    print(f"Processing {period} ...")

    cfg = param_map_2017[period]
    switch_dt = pd.to_datetime(cfg["switch_date"])

    # Pre-carica parametri prev/curr una sola volta
    Res_prev = load_res_cached(cfg["prev"])
    Res_curr = load_res_cached(cfg["curr"])

    gdp_actual = gdp_adv_estimate[period]
    news_output_file = f"news_Q/news_{period[:4]}_{period[4:]}.xlsx"

    results_list = []
    news_tables_dict = {}

    for i in range(1, len(vintages)):
        vintage_old = vintages[i-1]
        vintage_new = vintages[i]

        try:
            # Selezione parametri in base alla data del vintage_new
            v_new_dt = pd.to_datetime(vintage_new)
            Res_use = Res_prev if v_new_dt < switch_dt else Res_curr

            datafile_old = os.path.join('data','US_new', vintage_old + '.xlsx')
            datafile_new = os.path.join('data','US_new', vintage_new + '.xlsx')
            X_old, _, _ = load_data(datafile_old, Spec)
            X_new, Time, _ = load_data(datafile_new, Spec)

            results = update_nowcast2(
                X_old, X_new, Time, Spec, Res_use,
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
            sheet_name = vintage.replace("2017-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")
