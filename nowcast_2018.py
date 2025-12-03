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

#------------------------------------------------- True GDP values for 2018
gdp_adv_estimate = {
    "2018q1": 2.3,
    "2018q2": 4.1,
    "2018q3": 3.5,
    "2018q4": 2.6
}

#------------------------------------------------- Vintages per quarter for 2018
vintages_dict_2018 = {
    "2018q1": [
        "2017-12-01", "2017-12-08", "2017-12-15", "2017-12-22", "2017-12-29",
        "2018-01-05", "2018-01-12", "2018-01-19", "2018-01-26", "2018-02-02",
        "2018-02-09", "2018-02-16", "2018-02-23", "2018-03-02", "2018-03-09",
        "2018-03-16", "2018-03-23", "2018-03-30", "2018-04-06", "2018-04-13",
        "2018-04-20", "2018-04-27"
    ],
    "2018q2": [
        "2018-03-02", "2018-03-09", "2018-03-16", "2018-03-23", "2018-03-30",
        "2018-04-06", "2018-04-13", "2018-04-20", "2018-04-27", "2018-05-04",
        "2018-05-11", "2018-05-18", "2018-05-25", "2018-06-01", "2018-06-08",
        "2018-06-15", "2018-06-22", "2018-06-29", "2018-07-06", "2018-07-13",
        "2018-07-20", "2018-07-27"
    ],
    "2018q3": [
        "2018-06-01", "2018-06-08", "2018-06-15", "2018-06-22",
        "2018-06-29", "2018-07-06", "2018-07-13", "2018-07-20", "2018-07-27",
        "2018-08-03", "2018-08-10", "2018-08-17", "2018-08-24", "2018-08-31",
        "2018-09-07", "2018-09-14", "2018-09-21", "2018-09-28", "2018-10-05",
        "2018-10-12", "2018-10-19", "2018-10-26"
    ],
    "2018q4": [
        "2018-08-31", "2018-09-07", "2018-09-14", "2018-09-21", "2018-09-28", "2018-10-05",
        "2018-10-12", "2018-10-19", "2018-10-26", "2018-11-02", "2018-11-09",
        "2018-11-16", "2018-11-23", "2018-11-30", "2018-12-07", "2018-12-14",
        "2018-12-21", "2018-12-28", "2019-01-04", "2019-01-11", "2019-01-18",
        "2019-01-25",
    ]
}

#------------------------------------------------- Parametri per logica "fixed within quarter, re-estimate at quarter start"
param_map_2018 = {
    "2018q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20171002.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20180102.pickle"),
        "switch_date": "2018-01-01"
    },
    "2018q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20180102.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20180402.pickle"),
        "switch_date": "2018-04-01"
    },
    "2018q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20180402.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20180702.pickle"),
        "switch_date": "2018-07-01"
    },
    "2018q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20180702.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20181001.pickle"),
        "switch_date": "2018-10-01"
    }
}

#------------------------------------------------- Loop over quarters for 2018
for period, vintages in vintages_dict_2018.items():
    print(f"Processing {period} ...")

    cfg = param_map_2018[period]
    switch_dt = pd.to_datetime(cfg["switch_date"])

    with open(cfg["prev"], 'rb') as h1:
        Res_prev = pickle.load(h1)['Res']
    with open(cfg["curr"], 'rb') as h2:
        Res_curr = pickle.load(h2)['Res']

    gdp_actual = gdp_adv_estimate[period]
    news_output_file = f"news_Q/news_{period[:4]}_{period[4:]}.xlsx"

    results_list = []
    news_tables_dict = {}

    for i in range(1, len(vintages)):
        vintage_old = vintages[i-1]
        vintage_new = vintages[i]

        try:
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
            sheet_name = vintage.replace("2018-", "").replace("2019-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")
