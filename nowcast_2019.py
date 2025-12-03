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

#------------------------------------------------- True GDP values for 2019
gdp_adv_estimate = {
    "2019q1": 3.2,
    "2019q2": 2.1,
    "2019q3": 1.9,
    "2019q4": 2.1
}

#------------------------------------------------- Vintages per quarter for 2019
vintages_dict_2019 = {
    "2019q1": [
        "2018-11-30", "2018-12-07", "2018-12-14",
        "2018-12-21", "2018-12-28", "2019-01-04", "2019-01-11", "2019-01-18",
        "2019-01-25", "2019-02-01", "2019-02-08", "2019-02-15", "2019-02-22",
        "2019-03-01", "2019-03-08", "2019-03-15", "2019-03-22", "2019-03-29",
        "2019-04-05", "2019-04-12", "2019-04-19", "2019-04-26"
    ],

    "2019q2": [
        "2019-03-01", "2019-03-08", "2019-03-15",
        "2019-03-22", "2019-03-29", "2019-04-05", "2019-04-12", "2019-04-19",
        "2019-04-26", "2019-05-03", "2019-05-10", "2019-05-17", "2019-05-24",
        "2019-05-31", "2019-06-07", "2019-06-14", "2019-06-21", "2019-06-28",
        "2019-07-05", "2019-07-12", "2019-07-19", "2019-07-26"
    ],

    "2019q3": [
        "2019-06-07", "2019-06-14",
        "2019-06-21", "2019-06-28", "2019-07-05", "2019-07-12", "2019-07-19",
        "2019-07-26", "2019-08-02", "2019-08-09", "2019-08-16", "2019-08-23",
        "2019-08-30", "2019-09-06", "2019-09-13", "2019-09-20", "2019-09-27",
        "2019-10-04", "2019-10-11", "2019-10-18", "2019-10-25", "2019-11-01"
    ],

    "2019q4": [
        "2019-09-06", "2019-09-13",
        "2019-09-20", "2019-09-27", "2019-10-04", "2019-10-11", "2019-10-18",
        "2019-10-25", "2019-11-01", "2019-11-08", "2019-11-15", "2019-11-22",
        "2019-11-29", "2019-12-06", "2019-12-13", "2019-12-20", "2019-12-27",
        "2020-01-03", "2020-01-10", "2020-01-17", "2020-01-24", "2020-01-31"
    ]
}

#------------------------------------------------- Parametri per logica Fed (prev fino al 31/12, curr dal 01/01)
param_map_2019 = {
    "2019q1": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20181001.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20190102.pickle"),
        "switch_date": "2019-01-01"
    },
    "2019q2": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20190102.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20190401.pickle"),
        "switch_date": "2019-04-01"
    },
    "2019q3": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20190401.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20190701.pickle"),
        "switch_date": "2019-07-01"
    },
    "2019q4": {
        "prev": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20190701.pickle"),
        "curr": Path(r"C:\Users\Matteo17\OneDrive\Desktop\Nova SBE\Tesi\Nowcasting\DFM_quarter_param\ResDFM_20191001.pickle"),
        "switch_date": "2019-10-01"
    }
}

#------------------------------------------------- Loop over quarters for 2019
for period, vintages in vintages_dict_2019.items():
    print(f"Processing {period} ...")

    cfg = param_map_2019[period]
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
            sheet_name = vintage.replace("2019-", "").replace("2020-", "")
            df_news.to_excel(writer, sheet_name=sheet_name)
    print(f"Saved news tables to {news_output_file}")
