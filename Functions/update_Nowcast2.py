# -------------------------------------------------Libraries
from datetime import datetime as dt
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from Functions.update_Nowcast import News_DFM

from Functions.dfm import SKF, FIS


# -------------------------------------------------update_nowcast2
def update_nowcast2(X_old, X_new, Time, Spec, Res, series, period, vintage_old, vintage_new, display=True):
    # Convert vintage dates to ordinals
    if not isinstance(vintage_old, int):
        vintage_old = dt.strptime(vintage_old, '%Y-%m-%d').date().toordinal() + 366
    if not isinstance(vintage_new, int):
        vintage_new = dt.strptime(vintage_new, '%Y-%m-%d').date().toordinal() + 366

    # Make sure datasets are the same size
    N = np.shape(X_new)[1]
    T_old = np.shape(X_old)[0]
    T_new = np.shape(X_new)[0]

    if T_new > T_old:
        temp = np.zeros((T_new - T_old, N))
        temp[:] = np.nan
        X_old = np.vstack([X_old, temp])

    temp = np.zeros((12, N))
    temp[:] = np.nan
    X_old = np.vstack([X_old, temp])
    X_new = np.vstack([X_new, temp])

    future = np.array([(dt.fromordinal(Time[-1] - 366) +
                        relativedelta(months=+ i)).toordinal() + 366 for i in range(1, 13)])
    Time = np.hstack([Time, future])

    # Identify series index and frequency
    i_series = np.where(series == Spec.SeriesID)[0]
    freq = Spec.Frequency[i_series][0]

    if freq == 'm':
        y, m = period.split(freq)
        y, m = int(y), int(m)
        d = 1
        t_nowcast = np.where((dt(y, m, d).toordinal() + 366) == Time)[0]
    elif freq == 'q':
        y, q = period.split(freq)
        y, m = int(y), 3 * int(q)
        d = 1
        t_nowcast = np.where((dt(y, m, d).toordinal() + 366) == Time)[0]
    else:
        raise ValueError("Frequency value is not appropriate")

    if t_nowcast.size == 0:
        raise ValueError("Period is out of nowcasting horizon (up to one year ahead).")

    # Create revised dataset
    X_rev = X_new.copy()
    X_rev[np.isnan(X_old)] = np.nan

    # Compute news
    y_old, _, _, _, _, _, _, _, _ = News_DFM(X_old, X_rev, Res, t_nowcast, i_series)
    y_rev, y_new, _, actual, forecast, weight, _, _, _ = News_DFM(X_rev, X_new, Res, t_nowcast, i_series)

    # Compute impacts
    impact_revisions = y_rev - y_old
    news = actual - forecast
    impact_releases = weight * news

    # Build DataFrame of news
    news_table = pd.DataFrame({
        'Forecast': forecast.flatten('F'),
        'Actual': actual.flatten('F'),
        'Weight': weight.flatten('F'),
        'Impact': impact_releases.flatten('F')
    }, index=Spec.SeriesID)

    data_released = np.any(np.isnan(X_old) & ~np.isnan(X_new), 0)

    # Optional display
    if display:
        print("\n Nowcast Update: {}".format(dt.fromordinal(vintage_new - 366).isoformat()))
        print("\n Nowcast for: {} ({}), {}".format(Spec.SeriesName[i_series][0],
                                                   Spec.UnitsTransformed[i_series][0],
                                                   pd.to_datetime(dt.fromordinal(Time[t_nowcast][0] - 366)).to_period(
                                                       'Q')))
        print('\n Nowcast Impact Decomposition')
        print(' Note: The displayed output is subject to rounding error\n')
        print('              {} nowcast:              {:.5f}'.format(dt.fromordinal(vintage_old - 366).isoformat(),
                                                                     y_old[0]))
        print('      Impact from data revisions:      {:.5f}'.format(impact_revisions[0]))
        print('       Impact from data releases:      {:.5f}'.format(np.nansum(news_table.Impact)))
        print('                                     +_________')
        print(
            '                    Total impact:      {:.5f}'.format(impact_revisions[0] + np.nansum(news_table.Impact)))
        print('              {} nowcast:              {:.5f}'.format(dt.fromordinal(vintage_new - 366).isoformat(),
                                                                     y_new[0]))
        print('\n  Nowcast Detail Table \n')
        print(news_table.iloc[np.where(data_released)[0], :])

    # Return all relevant objects in a dictionary
    return {
        "y_old": y_old,
        "y_new": y_new,
        "impact_revisions": impact_revisions,
        "impact_releases": impact_releases,
        "news_table": news_table,
        "vintage_old": vintage_old,
        "vintage_new": vintage_new
    }
