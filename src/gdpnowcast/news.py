"""DFM news / nowcast-update step (Banbura-Modugno).

Typed, de-MATLAB port of Functions/update_Nowcast.py (News_DFM, para_const) and
the update_nowcast2 wrapper from Functions/update_Nowcast2.py (here renamed
update_nowcast). News_DFM and para_const are numeric and date-free, so they are
ported verbatim. The wrapper drops the MATLAB +366 ordinal arithmetic: Time is a
real pandas DatetimeIndex, the 12-month forecast horizon is built with
MonthBegin, and t_nowcast is found by Timestamp comparison -- the integer index
is identical to v1's, so News_DFM is unaffected.

API change (intentional, documented): the returned vintage_old/vintage_new are
pandas Timestamps, not MATLAB int ordinals.

Behaviour note: like v1, update_nowcast does NOT special-case the no-news /
already-observed vintages -- it computes `actual - forecast` unconditionally and
raises (TypeError/ValueError) when News_DFM returns no forecast. The backtest
runner (B7) replicates v1's blanket skip-on-error for those vintages; handling
them gracefully is a Phase-4 candidate. Golden parity: tests/test_news_golden.py
matches the frozen v1 2017q1 nowcast (18 vintages) at rtol=atol=1e-6.

Uppercase identifiers are econometric matrix notation; ruff N802/N803/N806 are
ignored for this file.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dfm import FIS, SKF
from .dfm_spec import DfmSpec


def update_nowcast(
    X_old: np.ndarray,
    X_new: np.ndarray,
    Time: pd.DatetimeIndex,
    Spec: DfmSpec,
    Res: dict,
    series: str,
    period: str,
    vintage_old: str | pd.Timestamp,
    vintage_new: str | pd.Timestamp,
    verbose: bool = False,
    mask_target: bool = False,
) -> dict:
    # Keep vintages as Timestamps (no MATLAB ordinal); used for display/return only.
    if not isinstance(vintage_old, pd.Timestamp):
        vintage_old = pd.Timestamp(vintage_old)
    if not isinstance(vintage_new, pd.Timestamp):
        vintage_new = pd.Timestamp(vintage_new)

    # Make sure datasets are the same size
    N = np.shape(X_new)[1]
    T_old = np.shape(X_old)[0]
    T_new = np.shape(X_new)[0]

    if T_new > T_old:
        temp = np.zeros((T_new - T_old, N))
        temp[:] = np.nan
        X_old = np.vstack([X_old, temp])

    # Append 1 year (12 months) of NaNs to each dataset to allow forecasting at
    # different horizons.
    temp = np.zeros((12, N))
    temp[:] = np.nan
    X_old = np.vstack([X_old, temp])
    X_new = np.vstack([X_new, temp])

    # Extend Time by 12 future month-starts (replaces the MATLAB +366 ordinal loop).
    future = pd.DatetimeIndex([Time[-1] + pd.offsets.MonthBegin(i) for i in range(1, 13)])
    Time = Time.append(future)

    # Identify series index and frequency
    i_series = np.where(series == Spec.SeriesID)[0]
    freq = Spec.Frequency[i_series][0]

    if freq == "m":
        y_str, m_str = period.split(freq)
        yr, mo = int(y_str), int(m_str)
        t_nowcast = np.where(Time == pd.Timestamp(yr, mo, 1))[0]
    elif freq == "q":
        y_str, q_str = period.split(freq)
        yr, mo = int(y_str), 3 * int(q_str)
        t_nowcast = np.where(Time == pd.Timestamp(yr, mo, 1))[0]
    else:
        raise ValueError("Frequency value is not appropriate")

    if t_nowcast.size == 0:
        raise ValueError("Period is out of nowcasting horizon (up to one year ahead).")

    if mask_target:
        # NY-Fed real-time discipline: the value being nowcast must never be in the
        # information set. NaN-out the single target cell (t_nowcast, i_series) in
        # BOTH datasets before the smoother runs, so the release-week vintage forecasts
        # the target instead of hitting the NO-FORECAST branch and reading back the
        # just-released advance. t_nowcast/i_series are 1-element arrays -> one cell.
        # X_old/X_new here are local (np.vstack-extended) copies, so the caller's
        # arrays are untouched. Masking X_old is inert within a single quarter (v_old
        # is always pre-release) but kept for quarters whose loop runs past the release.
        X_new[t_nowcast, i_series] = np.nan
        X_old[t_nowcast, i_series] = np.nan

    # Create revised dataset (new values restricted to the old data's NaN pattern)
    X_rev = X_new.copy()
    X_rev[np.isnan(X_old)] = np.nan

    # Compute news --------------------------------------------------------
    # Impact from data revisions
    y_old, _, _, _, _, _, _, _, _ = News_DFM(X_old, X_rev, Res, t_nowcast, i_series)
    # Impact from data releases
    y_rev, y_new, _, actual, forecast, weight, _, _, _ = News_DFM(
        X_rev, X_new, Res, t_nowcast, i_series
    )

    impact_revisions = y_rev - y_old  # Impact from revisions
    news = actual - forecast  # News from releases
    impact_releases = weight * news  # Impact of releases

    # Store results
    news_table = pd.DataFrame(
        {
            "Forecast": forecast.flatten("F"),
            "Actual": actual.flatten("F"),
            "Weight": weight.flatten("F"),
            "Impact": impact_releases.flatten("F"),
        },
        index=Spec.SeriesID,
    )

    # Select only series with updates
    data_released = np.any(np.isnan(X_old) & ~np.isnan(X_new), 0)

    # Display the impact decomposition
    if verbose:
        period_q = pd.to_datetime(Time[t_nowcast][0]).to_period("Q")
        total = impact_revisions[0] + np.nansum(news_table.Impact)
        print(f"\n Nowcast Update: {vintage_new.date().isoformat()}")
        print(
            f"\n Nowcast for: {Spec.SeriesName[i_series][0]} "
            f"({Spec.UnitsTransformed[i_series][0]}), {period_q}"
        )
        print("\n Nowcast Impact Decomposition")
        print(" Note: The displayed output is subject to rounding error\n")
        print(
            f"              {vintage_old.date().isoformat()} nowcast:              {y_old[0]:.5f}"
        )
        print(f"      Impact from data revisions:      {impact_revisions[0]:.5f}")
        print(f"       Impact from data releases:      {np.nansum(news_table.Impact):.5f}")
        print("                                     +_________")
        print(f"                    Total impact:      {total:.5f}")
        print(
            f"              {vintage_new.date().isoformat()} nowcast:              {y_new[0]:.5f}"
        )
        print("\n  Nowcast Detail Table \n")
        print(news_table.iloc[np.where(data_released)[0], :])

    return {
        "y_old": y_old,
        "y_new": y_new,
        "impact_revisions": impact_revisions,
        "impact_releases": impact_releases,
        "news_table": news_table,
        "vintage_old": vintage_old,
        "vintage_new": vintage_new,
    }


def News_DFM(
    X_old: np.ndarray, X_new: np.ndarray, Res: dict, t_fcst: np.ndarray, v_news: np.ndarray
) -> tuple:
    # News_DFM()    Calculates changes in news. Inputs two datasets, DFM
    # parameters, target time index and target variable index; produces nowcast
    # updates and decomposes the change into news.

    # Initialize variables
    r = Res["C"].shape[1]
    N = X_new.shape[1]
    singlenews = np.zeros((1, N))  # News vector (will store news for each series)

    # NO FORECAST CASE: Already values for variables v_news at time t_fcst
    if ~np.isnan(X_new[t_fcst, v_news])[0]:
        Res_old = para_const(X_old, Res, 0)  # Apply Kalman filter for old data

        y_old = np.zeros((1, v_news.shape[0]))
        y_new = np.zeros((1, v_news.shape[0]))
        for i in range(v_news.shape[0]):  # Loop for each target variable
            # (Observed value) - (predicted value)
            singlenews[:, v_news[i]] = X_new[t_fcst, v_news[i]] - Res_old["X_sm"][t_fcst, v_news[i]]

            # Set predicted and observed y values
            y_old[0, i] = Res_old["X_sm"][t_fcst, v_news[i]].copy()
            y_new[0, i] = X_new[t_fcst, v_news[i]].copy()

        # Forecast-related output set to empty
        return y_old, y_new, singlenews, None, None, None, None, None, None

    else:
        # FORECAST CASE (broken down into (A) and (B))

        # Initialize series mean/standard deviation respectively
        Mx = Res["Mx"].reshape((-1, 1))
        Wx = Res["Wx"].reshape((-1, 1))

        # Calculate indicators for missing values (1 if missing, 0 otherwise)
        miss_old = np.isnan(X_old).astype(np.int64)
        miss_new = np.isnan(X_new).astype(np.int64)

        # Indicator for missing--combine to a single matrix where:
        # (i) -1: in old data, missing in new; (ii) 1: in new, missing in old;
        # (iii) 0: missing from/available in both.
        i_miss = miss_old - miss_new

        # Time/variable indices where case (b) is true
        t_miss, v_miss = np.where(i_miss == 1)
        ordered_col = v_miss.argsort()
        t_miss, v_miss = t_miss[ordered_col], v_miss[ordered_col]

        # FORECAST SUBCASE (A): NO NEW INFORMATION
        if v_miss.shape[0] == 0:
            # Fill in missing variables using a Kalman filter
            Res_old = para_const(X_old, Res, 0)
            Res_new = para_const(
                X_new, Res, 0
            )  # v1 computes but never uses this (kept for fidelity)

            # Set predicted and observed y values. New y value is set to old
            y_old = Res_old["X_sm"][t_fcst, v_news]
            y_new = y_old.copy()

            # No news, so nothing returned for news-related output
            return y_old, y_new, singlenews, None, None, None, None, None, None

        else:
            # FORECAST SUBCASE (B): NEW INFORMATION

            # Difference between forecast time and new data time
            lag = t_fcst - t_miss

            # Gives biggest time interval between forecast and new data
            k = np.max(np.hstack([np.abs(lag), np.max(lag) - np.min(lag)]))

            C = Res["C"].copy()  # Observation matrix
            R = Res["R"].copy()  # Covariance for observation matrix residuals

            # Number of new events
            n_news = lag.shape[0]

            # Smooth old dataset
            Res_old = para_const(X_old, Res, k)
            Plag = Res_old["Plag"].copy()

            # Smooth new dataset
            Res_new = para_const(X_new, Res, 0)

            # Subset for target variable and forecast time
            y_old = Res_old["X_sm"][t_fcst, v_news]
            y_new = Res_new["X_sm"][t_fcst, v_news]

            for i in range(n_news):  # Cycle through total number of updates
                h = abs(t_fcst - t_miss[i])[0]
                m = np.maximum(t_miss[i], t_fcst)[0]

                # If location of update is later than the forecasting date
                if t_miss[i] > t_fcst:
                    Pp = Plag[h][m].copy()
                else:
                    Pp = Plag[h][m].T.copy()
                if i == 0:
                    # Initialize projection onto updates
                    P1 = np.matmul(Pp, C[[v_miss[i]]][:, :r].T)
                else:
                    # Projection on updates
                    P1 = np.hstack([P1, np.matmul(Pp, C[[v_miss[i]]][:, :r].T)])

            for i in range(t_miss.shape[0]):
                # Standardize predicted and observed values
                X_new_norm = (X_new[t_miss[i], v_miss[i]] - Mx[v_miss[i]]) / Wx[v_miss[i]]
                X_sm_norm = (Res_old["X_sm"][t_miss[i], v_miss[i]] - Mx[v_miss[i]]) / Wx[v_miss[i]]

                # Innovation: [observed] data - [predicted data]
                if i == 0:
                    innov = X_new_norm - X_sm_norm
                else:
                    innov = np.hstack([innov, X_new_norm - X_sm_norm])
            innov = innov.reshape((1, -1))

            WW = np.zeros((v_miss[-1] + 1, v_miss[-1] + 1))
            WW[:] = np.nan

            # Gives non-standardized series weights
            for i in range(lag.shape[0]):
                for j in range(lag.shape[0]):
                    h = abs(lag[i] - lag[j])
                    m = max(t_miss[i], t_miss[j])

                    if t_miss[j] > t_miss[i]:
                        Pp = Plag[h][m].copy()
                    else:
                        Pp = Plag[h][m].T.copy()

                    if v_miss[i] == v_miss[j] and t_miss[i] != t_miss[j]:
                        WW[v_miss[i], v_miss[j]] = 0
                    else:
                        WW[v_miss[i], v_miss[j]] = R[v_miss[i], v_miss[j]].copy()

                    if j == 0:
                        p2 = (
                            np.matmul(np.matmul(C[[v_miss[i]]][:, :r], Pp), C[[v_miss[j]]][:, :r].T)
                            + WW[v_miss[i], v_miss[j]]
                        )
                    else:
                        p2 = np.hstack(
                            [
                                p2,
                                np.matmul(
                                    np.matmul(C[[v_miss[i]]][:, :r], Pp), C[[v_miss[j]]][:, :r].T
                                )
                                + WW[v_miss[i], v_miss[j]],
                            ]
                        )
                if i == 0:
                    P2 = p2.copy()
                else:
                    P2 = np.vstack([P2, p2])

            for i in range(v_news.shape[0]):  # loop on v_news
                # Convert to real units (unstandardized data)
                if i == 0:
                    totnews = np.matmul(
                        np.matmul(
                            np.matmul(np.matmul(Wx[[v_news[i]]], C[[v_news[i]]][:, :r]), P1),
                            np.linalg.inv(P2),
                        ),
                        innov.T,
                    )
                    temp = (
                        np.matmul(
                            np.matmul(np.matmul(Wx[[v_news[i]]], C[[v_news[i]]][:, :r]), P1),
                            np.linalg.inv(P2),
                        )
                        * innov
                    )
                    gain = np.matmul(
                        np.matmul(np.matmul(Wx[[v_news[i]]], C[[v_news[i]]][:, :r]), P1),
                        np.linalg.inv(P2),
                    )

                    temp = temp.reshape((1, *temp.shape))
                    gain = gain.reshape((1, *gain.shape))
                else:
                    temp_A = np.matmul(
                        np.matmul(
                            np.matmul(np.matmul(Wx[v_news[i]], C[[v_news[i]]][:, :r]), P1),
                            np.linalg.inv(P2),
                        ),
                        innov.T,
                    )
                    temp_B = (
                        np.matmul(
                            np.matmul(np.matmul(Wx[v_news[i]], C[[v_news[i]]][:, :r]), P1),
                            np.linalg.inv(P2),
                        )
                        * innov
                    )
                    temp_C = np.matmul(
                        np.matmul(np.matmul(Wx[v_news[i]], C[[v_news[i]]][:, :r]), P1),
                        np.linalg.inv(P2),
                    )

                    totnews = np.hstack([totnews, temp_A])
                    temp = np.vstack([temp, temp_B[np.newaxis,]])
                    gain = np.vstack([gain, temp_C[np.newaxis,]])

            # Initialize output objects
            singlenews = np.zeros((v_news.shape[0], np.max(t_miss) - np.min(t_miss) + 1, N))
            actual = np.zeros((N, 1))
            forecast = np.zeros((N, 1))
            weight = np.zeros((v_news.shape[0], N, 1))
            singlenews[:], actual[:], forecast[:], weight[:] = np.nan, np.nan, np.nan, np.nan

            # Fill in output values
            for i in range(innov.shape[1]):
                actual[v_miss[i], 0] = X_new[t_miss[i], v_miss[i]].copy()
                forecast[v_miss[i], 0] = Res_old["X_sm"][t_miss[i], v_miss[i]].copy()

                for j in range(v_news.shape[0]):
                    singlenews[j, t_miss[i] - min(t_miss), v_miss[i]] = temp[j, 0, i].copy()
                    weight[j, v_miss[i], :] = gain[j, :, i] / Wx[v_miss[i]]

            singlenews = np.sum(singlenews, axis=0)  # Returns total news
            v_miss = np.sort(np.unique(v_miss))

    return y_old, y_new, singlenews, actual, forecast, weight[0], t_miss, v_miss, innov


def para_const(X: np.ndarray, P: dict, lag: int) -> dict:
    # para_const()    Kalman filter for the news calculation step. Smooths and
    # fills in missing data for X using already-estimated model parameters P (in
    # contrast to runKF(), used during estimation).

    # Set model parameters
    Z_0 = P["Z_0"].copy()
    V_0 = P["V_0"].copy()
    A = P["A"].copy()
    C = P["C"].copy()
    Q = P["Q"].copy()
    R = P["R"].copy()
    Mx = P["Mx"].copy()
    Wx = P["Wx"].copy()

    # Prepare data
    T = X.shape[0]

    # Standardise x
    Y = ((X - np.tile(Mx, (T, 1))) / np.tile(Wx, (T, 1))).T

    # Apply Kalman filter and smoother (see runKF() for FIS / SKF details)
    Sf = SKF(Y, A, C, Q, R, Z_0, V_0)  # Kalman filter
    Ss = FIS(A, Sf)  # Smoothing step

    # Calculate parameter output
    Vs = Ss["VmT"][1:, :, :].copy()  # Smoothed factor covariance for transition matrix
    Vf = Ss["VmU"][1:, :, :].copy()  # Filtered factor posterior covariance
    Zsmooth = Ss["ZmT"].copy()  # Smoothed factors
    Vsmooth = Ss["VmT"].copy()  # Smoothed covariance values

    Plag = [Vs.copy()]

    for jk in range(lag):
        Plag.append(np.zeros(Vs.shape))
        for jt in range(Plag[0].shape[0] - 1, lag - 1, -1):
            As = np.matmul(
                np.matmul(Vf[jt - jk - 1], A.T),
                np.linalg.pinv(np.matmul(np.matmul(A, Vf[jt - jk - 1]), A.T) + Q),
            )
            Plag[jk + 1][jt] = np.matmul(As, Plag[jk][jt])

    # Prepare data for output
    Zsmooth = Zsmooth.T

    x_sm = np.matmul(Zsmooth[1:, :], C.T)  # Factors to series representation
    X_sm = np.tile(Wx, (T, 1)) * x_sm + np.tile(Mx, (T, 1))  # Standardized to unstandardized

    # Loading dictionary with the results
    Res = {"Plag": Plag, "P": Vsmooth, "X_sm": X_sm, "F": Zsmooth[1:, :]}

    return Res
