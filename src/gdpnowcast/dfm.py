"""Banbura-Modugno mixed-frequency dynamic factor model (EM + Kalman).

Typed, de-MATLAB port of Functions/dfm.py. Behaviour-preserving changes only:
  * imports rem_nans_spline from ._dfm_support (was Functions.remNaNs_spline);
  * the duplicate ``max_iter = 5000`` reassignment that ignored the argument is
    removed (no-op for the golden, which runs at the 5000 cap);
  * em_converged's ``print(...).format(...)`` bug (AttributeError on a
    likelihood decrease) is fixed to ``print(...format(...))``;
  * the ``(1,1)``-array -> scalar ``.item()`` shims from A0 are kept;
  * the Table-3..7 / progress ``print`` side-effects are gated behind
    ``verbose`` (default False); no numerics changed.

Golden parity vs the A0-shimmed v1 estimator at rtol=atol=1e-6
(tests/test_dfm_golden.py). Uppercase identifiers (X, T, N, A, C, Q, R, ...)
are econometric matrix notation; ruff N803/N806 are ignored for this file.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.linalg import block_diag, eig

from ._dfm_support import rem_nans_spline
from .dfm_spec import DfmSpec


# region DFM core
def dfm(
    X: np.ndarray,
    Spec: DfmSpec,
    threshold: float = 1e-5,
    max_iter: int = 5000,
    verbose: bool = False,
) -> dict:
    # DFM()    Runs the dynamic factor model
    #
    #  Description:
    #   DFM() inputs the organized and transformed data X and parameter
    #   structure Par, and outputs the dynamic factor model structure Res plus
    #   data summary statistics (mean and standard deviation).
    #
    # References:
    #   Marta Banbura, Domenico Giannone and Lucrezia Reichlin, Nowcasting
    #   (2010), in Clements & Hendry (eds), Oxford Handbook on Economic
    #   Forecasting.

    ## Store model parameters ------------------------------------------------

    # DFM input specifications: See documentation for details
    Par: dict = {}
    Par["blocks"] = Spec.Blocks.copy()  # Block loading structure
    Par["nQ"] = (Spec.Frequency == "q").sum()  # Number of quarterly series
    Par["p"] = 1  # Number of lags in autoregressive of factor (same for all factors)
    Par["r"] = np.ones((1, Spec.Blocks.shape[1])).astype(np.int64)  # Common factors per block

    if verbose:
        print("\n\n\n")
        print("Table 3: Block Loading Structure")
        print(pd.DataFrame(data=Spec.Blocks, index=Spec.SeriesName, columns=Spec.BlockNames))
        print("\n")
        print("Estimating the dynamic factor model (DFM) \n\n")

    T, N = X.shape
    r = Par["r"].copy()
    p = Par["p"]
    nQ = Par["nQ"]
    blocks = Par["blocks"].copy()

    i_idio = np.append(np.ones(N - nQ), np.zeros(nQ)).reshape((-1, 1), order="F") == 1

    # R*Lambda = q; Constraints on the loadings of the quarterly variables
    R_mat = np.array([2, -1, 0, 0, 0, 3, 0, -1, 0, 0, 2, 0, 0, -1, 0, 1, 0, 0, 0, -1]).reshape(
        (4, 5)
    )
    q = np.zeros((4, 1))

    # Prepare data -----------------------------------------------------------
    Mx = np.nanmean(X, axis=0)
    Wx = np.nanstd(X, axis=0, ddof=1)
    xNaN = (X - np.tile(Mx, (T, 1))) / np.tile(Wx, (T, 1))

    # Initial Conditions------------------------------------------------------
    optNaN: dict = {}
    optNaN["method"] = 2  # Remove leading and closing zeros
    optNaN["k"] = 3  # Setting for filter(): See rem_nans_spline

    A, C, Q, R, Z_0, V_0 = InitCond(
        xNaN.copy(), r.copy(), p, blocks.copy(), optNaN, R_mat.copy(), q, nQ, i_idio.copy()
    )

    # initialize EM loop values
    previous_loglik = -np.inf
    num_iter = 0
    LL = [-np.inf]
    converged = 0

    # y for the estimation is with missing data
    y = xNaN.copy().T

    # EM LOOP ----------------------------------------------------------------
    # The model can be written as
    #   y = C*Z + e;  Z = A*Z(-1) + v
    # where y is NxT, Z is (pr)xT, etc.

    # Remove the leading and ending nans
    optNaN["method"] = 3
    y_est, _ = rem_nans_spline(xNaN.copy(), optNaN)
    y_est = y_est.T

    while num_iter < max_iter and not converged:  # Loop until convergence or max iter.
        # Applying EM algorithm
        C_new, R_new, A_new, Q_new, Z_0, V_0, loglik = EMstep(
            y_est, A, C, Q, R, Z_0, V_0, r, p, R_mat, q, nQ, i_idio, blocks
        )

        C = C_new.copy()
        R = R_new.copy()
        A = A_new.copy()
        Q = Q_new.copy()

        if num_iter > 2:  # Check convergence
            converged, _decrease = em_converged(loglik, previous_loglik, threshold, 1)

        if verbose and (num_iter % 10) == 0 and num_iter > 0:
            print(f"Now running the {num_iter}th iteration of max {max_iter}")
            print(
                f"Loglik: {loglik} (% Change: {100 * ((loglik - previous_loglik) / previous_loglik)})"
            )

        LL.append(loglik)
        previous_loglik = loglik
        num_iter += 1

    if verbose:
        if num_iter < max_iter:
            print(f"Successful: Convergence at {num_iter} interations")
        else:
            print("Stopped because maximum iterations reached")

    # Final run of the Kalman filter
    Zsmooth, _, _, _ = runKF(y, A, C, Q, R, Z_0, V_0)
    Zsmooth = Zsmooth.T
    x_sm = np.matmul(Zsmooth[1:, :], C.T)  # Get smoothed X

    # Loading the structure with the results --------------------------------
    Res = {
        "x_sm": x_sm.copy(),
        "X_sm": np.tile(Wx, (T, 1)) * x_sm + np.tile(Mx, (T, 1)),
        "Z": Zsmooth[1:, :].copy(),
        "C": C.copy(),
        "R": R.copy(),
        "A": A.copy(),
        "Q": Q.copy(),
        "Mx": Mx.copy(),
        "Wx": Wx.copy(),
        "Z_0": Z_0.copy(),
        "V_0": V_0.copy(),
        "r": r,
        "p": p,
        "loglik": LL,
    }

    # Display output: tables with names, factor loadings and AR coefficients.
    if verbose:
        nQ = Par["nQ"]
        nM = Spec.SeriesID.shape[0] - nQ
        nFactors = np.sum(Par["r"])

        print("\n Table 4: Factor Loadings for Monthly Series")
        print(
            pd.DataFrame(
                Res["C"][:nM, np.arange(0, nFactors * 5, 5)],
                columns=Spec.BlockNames,
                index=Spec.SeriesName[:nM],
            )
        )

        print("\n Table 5: Quarterly Loadings Sample (Global Factor)")
        print(
            pd.DataFrame(
                Res["C"][(-1 - nQ + 1) :, :5],
                columns=["f1_lag0", "f1_lag1", "f1_lag2", "f1_lag3", "f1_lag4"],
                index=Spec.SeriesName[-1 - nQ + 1 :],
            )
        )

        # AR model on factors (AR parameter and variance of residuals)
        A_terms = np.diag(Res["A"]).copy()
        Q_terms = np.diag(Res["Q"]).copy()

        print("\n Table 6: Autoregressive Coefficients on Factors")
        print(
            pd.DataFrame(
                {
                    "AR_Coefficient": A_terms[np.arange(0, nFactors * 5, 5)].copy(),
                    "Variance_Residual": Q_terms[np.arange(0, nFactors * 5, 5)].copy(),
                },
                index=Spec.BlockNames,
            )
        )

        # AR model on idiosyncratic errors
        print("\n Table 7: Autoregressive Coefficients on Idiosyncratic Component")
        A_len = A.shape[0]
        Q_len = Q.shape[0]

        A_index = np.hstack(
            [np.arange(nFactors * 5, nFactors * 5 + nM), np.arange(nFactors * 5 + nM, A_len, 5)]
        )
        Q_index = np.hstack(
            [np.arange(nFactors * 5, nFactors * 5 + nM), np.arange(nFactors * 5 + nM, Q_len, 5)]
        )

        print(
            pd.DataFrame(
                {
                    "AR_Coefficient": A_terms[A_index].copy(),
                    "Variance_Residual": Q_terms[Q_index].copy(),
                },
                index=Spec.SeriesName,
            )
        )

    return Res


# endregion


# region InitCond
def InitCond(
    x: np.ndarray,
    r: np.ndarray,
    p: int,
    blocks: np.ndarray,
    optNaN: dict,
    Rcon: np.ndarray,
    q: np.ndarray,
    nQ: int,
    i_idio: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # InitCond()  Calculates initial conditions for parameter estimation.
    #   Given standardized data and model information, builds initial parameter
    #   estimates used as inputs to the EM algorithm.

    pC = Rcon.shape[1]  # 'tent' structure size (quarterly to monthly)
    ppC = max(p, pC)
    n_b = blocks.shape[1]  # Number of blocks

    xBal, indNaN = rem_nans_spline(x.copy(), optNaN)  # Spline without NaNs

    T, N = xBal.shape  # Time T, series number N
    nM = N - nQ  # Number of monthly series

    xNaN = xBal.copy()
    xNaN[indNaN] = np.nan  # Set missing values equal to NaNs
    res = xBal.copy()  # Spline output; later used for residuals
    resNaN = xNaN.copy()  # Later used for residuals

    # Initialize model coefficient output
    C: Any = None
    A: Any = None
    Q: Any = None
    V_0: Any = None

    # Set the first observations as NaNs: For quarterly-monthly aggreg. scheme
    indNaN[: pC - 1, :] = np.True_

    for i in range(n_b):  # Loop for each block
        r_i = r[0, i].copy()  # r_i = 1 when block is loaded

        # Observation equation -----------------------------------------------
        C_i = np.zeros((N, r_i * ppC))  # Initialize state variable matrix helper
        idx_i = np.where(blocks[:, i])[0]  # Series index loading block i
        idx_iM = idx_i[idx_i < nM]  # Monthly series indices for loaded blocks
        idx_iQ = idx_i[idx_i >= nM]  # Quarterly series indices for loaded blocks

        # Returns eigenvector v w/largest eigenvalue d
        d, v = eig(np.cov(res[:, idx_iM], rowvar=False))
        e_idx = np.where(d == np.max(d))[0]
        d = d[e_idx]
        v = v[:, e_idx]

        # Flip sign for cleaner output. Gives equivalent results without this.
        if np.sum(v) < 0:
            v = -v

        # For monthly series with loaded blocks (rows), replace with eigenvector
        C_i[idx_iM, 0:r_i] = v.copy()
        f = np.matmul(res[:, idx_iM], v)  # Data projection for eigenvector direction
        F = np.array(f[(pC - 1) : f.shape[0], :]).reshape((-1, 1))

        # Lag matrix using loading. Used later for quarterly series
        for kk in range(1, max(p + 1, pC)):
            F = np.concatenate((F, f[(pC - 1) - kk : f.shape[0] - kk, :]), axis=1)

        Rcon_i = np.kron(Rcon, np.eye(r_i))  # Quarterly-monthly aggregation scheme
        q_i = np.kron(q, np.zeros((r_i, 1)))

        # Produces projected data with lag structure (so pC-1 fewer entries)
        ff = F[:, 0 : (r_i * pC)].copy()

        for j in idx_iQ:  # Loop for quarterly variables
            # For series j, values are dropped to accommodate lag structure
            xx_j = resNaN[(pC - 1) :, j].copy()

            if sum(~np.isnan(xx_j)) < (ff.shape[1] + 2):
                xx_j = res[(pC - 1) :, j].copy()

            ff_j = ff[~np.isnan(xx_j), :].copy()
            xx_j = xx_j[~np.isnan(xx_j)].reshape((-1, 1)).copy()

            iff_j = np.linalg.inv(np.matmul(ff_j.T, ff_j))
            Cc = np.matmul(np.matmul(iff_j, ff_j.T), xx_j)

            a1 = np.matmul(iff_j, Rcon_i.T)
            a2 = np.linalg.inv(np.matmul(np.matmul(Rcon_i, iff_j), Rcon_i.T))
            a3 = np.matmul(Rcon_i, Cc) - q_i

            # Spline data monthly to quarterly conversion
            Cc = Cc - np.matmul(np.matmul(a1, a2), a3)

            C_i[j, 0 : pC * r_i] = Cc.T.copy()  # Place in output matrix

        # Zeros in first pC-1 entries (replace dropped from lag)
        ff = np.concatenate([np.zeros((pC - 1, pC * r_i)), ff], axis=0)

        # Residual Calculations
        res = res - np.matmul(ff, C_i.T)
        resNaN = res.copy()
        resNaN[indNaN] = np.nan

        # Combine past loadings together
        if i == 0:
            C = C_i.copy()
        else:
            C = np.hstack([C, C_i.copy()])

        # Transition equation ------------------------------------------------
        z = F[:, r_i - 1].copy()  # Projected data (no lag)
        Z = F[:, r_i : (r_i * (p + 1))].copy()  # Data with lag 1

        A_i = np.zeros((r_i * ppC, r_i * ppC)).T  # Initialize transition matrix
        A_temp = np.matmul(np.matmul(np.linalg.inv(np.matmul(Z.T, Z)), Z.T), z)  # OLS AR(p)

        A_i[:r_i, : r_i * p] = A_temp.T.copy()
        A_i[r_i:, : r_i * (ppC - 1)] = np.eye(r_i * (ppC - 1))

        Q_i = np.zeros((ppC * r_i, ppC * r_i))
        e = z - np.matmul(Z, A_temp)  # VAR residuals
        Q_i[:r_i, :r_i] = np.cov(e, rowvar=False)  # VAR covariance matrix

        initV_i = np.reshape(
            np.matmul(
                np.linalg.inv(np.eye((r_i * ppC) ** 2) - np.kron(A_i, A_i)),
                Q_i.flatten("F").reshape((-1, 1)),
            ),
            (r_i * ppC, r_i * ppC),
        )

        # Gives top left block for the transition matrix
        if i == 0:
            A = A_i.copy()
            Q = Q_i.copy()
            V_0 = initV_i.copy()
        else:
            A = block_diag(A, A_i)
            Q = block_diag(Q, Q_i)
            V_0 = block_diag(V_0, initV_i)

    eyeN = np.eye(N)[:, i_idio.flatten("F")]  # Used inside observation matrix

    C = np.hstack([C, eyeN])
    # Monthly-quarterly aggregation scheme
    C = np.hstack(
        [
            C,
            np.vstack(
                [
                    np.zeros((nM, 5 * nQ)),
                    np.kron(np.eye(nQ), np.array([1, 2, 3, 2, 1]).reshape((1, -1))),
                ]
            ),
        ]
    )
    # Initialize covariance matrix for transition matrix
    R = np.diag(np.nanvar(resNaN, ddof=1, axis=0))

    ii_idio = np.where(i_idio)[0]  # Indices for monthly variables
    n_idio = ii_idio.shape[0]  # Number of monthly variables
    BM = np.zeros((n_idio, n_idio))  # Monthly transition matrix values
    SM = np.zeros((n_idio, n_idio))  # Monthly residual covariance matrix values

    for i in range(n_idio):  # Loop for monthly variables
        # Set observation equation residual covariance matrix diagonal
        R[ii_idio[i], ii_idio[i]] = 1e-4

        # Subsetting series residuals for series i
        res_i = resNaN[:, ii_idio[i]].copy()

        # Returns number of leading/ending zeros
        try:
            leadZero = np.max(np.where(np.arange(1, T + 1) == np.cumsum(np.isnan(res_i)))) + 1
        except ValueError:
            leadZero = None

        try:
            endZero = -(
                np.max(np.where(np.arange(1, T + 1) == np.cumsum(np.isnan(res_i[::-1])))[0]) + 1
            )
        except ValueError:
            endZero = None

        # Truncate leading and ending zeros
        res_i = res[:, ii_idio[i]].copy()
        res_i = res_i[:endZero]
        res_i = res_i[leadZero:].reshape((-1, 1), order="F")

        # Linear regression: AR 1 process for monthly series residuals
        BM[i, i] = np.matmul(
            np.matmul(np.linalg.inv(np.matmul(res_i[:-1].T, res_i[:-1])), res_i[:-1].T), res_i[1:]
        ).item()
        SM[i, i] = np.cov(res_i[1:] - (res_i[:-1] * BM[i, i]), rowvar=False).item()

    Rdiag = np.diag(R).copy()
    sig_e = Rdiag[nM:] / 19
    Rdiag[nM:] = 1e-4
    R = np.diag(Rdiag).copy()  # Covariance for obs matrix residuals

    # For BQ, SQ
    rho0 = np.array([[0.1]])
    temp = np.zeros((5, 5))
    temp[0, 0] = 1

    # Blocks for covariance matrices
    SQ = np.kron(np.diag((1 - rho0[0, 0] ** 2) * sig_e), temp)
    BQ = np.kron(
        np.eye(nQ),
        np.vstack([np.hstack([rho0, np.zeros((1, 4))]), np.hstack([np.eye(4), np.zeros((4, 1))])]),
    )

    initViQ = np.matmul(
        np.linalg.inv(np.eye((5 * nQ) ** 2) - np.kron(BQ, BQ)), SQ.reshape((-1, 1))
    ).reshape((5 * nQ, 5 * nQ))
    initViM = np.diag(1 / np.diag(np.eye(BM.shape[0]) - BM**2)) * SM

    # Output
    A = block_diag(A, BM, BQ)
    Q = block_diag(Q, SM, SQ)
    Z_0 = np.zeros((A.shape[0], 1))
    V_0 = block_diag(V_0, initViM, initViQ)

    return A, C, Q, R, Z_0, V_0


# endregion


# region EM step
def EMstep(
    y: np.ndarray,
    A: np.ndarray,
    C: np.ndarray,
    Q: np.ndarray,
    R: np.ndarray,
    Z_0: np.ndarray,
    V_0: np.ndarray,
    r: np.ndarray,
    p: int,
    R_mat: np.ndarray,
    q: np.ndarray,
    nQ: int,
    i_idio: np.ndarray,
    blocks: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    # EMstep    Applies EM algorithm for parameter reestimation (Banbura &
    # Modugno, 2010). (1) E-step: expected log-likelihood from previous
    # parameters; (2) M-step: parameters re-estimated by maximisation.

    # Store series/model values
    n, T = y.shape
    nM = n - nQ
    pC = R_mat.shape[1]
    ppC = max(p, pC)
    num_blocks = blocks.shape[1]

    # ESTIMATION STEP: run the Kalman filter/smoother with current parameters.
    # Note the log-likelihood is NOT re-estimated after runKF: this effectively
    # gives the previous iteration's log-likelihood.
    Zsmooth, Vsmooth, VVsmooth, loglik = runKF(y, A, C, Q, R, Z_0, V_0)

    # MAXIMIZATION STEP (TRANSITION EQUATION)
    A_new = A.copy()
    Q_new = Q.copy()
    V_0_new = V_0.copy()

    # 2A. UPDATE FACTOR PARAMETERS INDIVIDUALLY ----------------------------
    for i in range(num_blocks):  # Loop for each block: factors are uncorrelated
        # SETUP INDEXING
        r_i = r[0, i].copy()  # r_i = 1 if block is loaded
        rp = r_i * p
        rp1 = np.sum(r[0, :i]) * ppC
        b_subset = np.arange(rp1, rp1 + rp)  # Subset blocks
        t_start = rp1  # Transition matrix factor idx start
        t_end = rp1 + r_i * ppC  # Transition matrix factor idx end

        # ESTIMATE FACTOR PORTION OF Q, A (eqns 6 and 8 in BM 2010)
        # E[f_t*f_t' | Omega_T]
        EZZ = np.matmul(Zsmooth[b_subset, 1:], Zsmooth[b_subset, 1:].T) + np.sum(
            Vsmooth[1:, [b_subset], [b_subset]], axis=0
        )

        # E[f_{t-1}*f_{t-1}' | Omega_T]
        EZZ_BB = np.matmul(Zsmooth[b_subset, :-1], Zsmooth[b_subset, :-1].T) + np.sum(
            Vsmooth[:-1, [b_subset], [b_subset]], axis=0
        )

        # E[f_t*f_{t-1}' | Omega_T]
        EZZ_FB = np.matmul(Zsmooth[b_subset, 1:], Zsmooth[b_subset, :-1].T) + np.sum(
            VVsmooth[:, b_subset, b_subset], axis=0
        )

        # Select transition matrix/covariance matrix for block i
        A_i = A[t_start:t_end, t_start:t_end].copy()
        Q_i = Q[t_start:t_end, t_start:t_end].copy()

        # Equation 6: Estimate VAR(p) for factor
        A_i[:r_i, :rp] = np.matmul(EZZ_FB[:r_i, :rp], np.linalg.inv(EZZ_BB[:rp, :rp]))

        # Equation 8: Covariance matrix of residuals of VAR
        Q_i[:r_i, :r_i] = (EZZ[:r_i, :r_i] - np.matmul(A_i[:r_i, :rp], EZZ_FB[:r_i, :rp].T)) / T

        # Place updated results in output matrix
        A_new[t_start:t_end, t_start:t_end] = A_i.copy()
        Q_new[t_start:t_end, t_start:t_end] = Q_i.copy()
        V_0_new[t_start:t_end, t_start:t_end] = Vsmooth[0, t_start:t_end, t_start:t_end].copy()

    # B. UPDATING PARAMETERS FOR IDIOSYNCRATIC COMPONENT ------------------
    rp1 = np.sum(r) * ppC  # Col size of factor portion
    niM = np.sum(i_idio[:nM])  # Number of monthly values
    t_start = rp1  # Start of idiosyncratic component index
    i_subset = np.arange(t_start, rp1 + niM)  # Indices for monthly idiosyncratic component values

    # Estimate the idiosyncratic component (eqns 6, 8 BM 2010)
    # E[f_t*f_t' | Omega_T]
    EZZ = np.diag(np.diag(np.matmul(Zsmooth[t_start:, 1:], Zsmooth[t_start:, 1:].T))) + np.diag(
        np.diag(np.sum(Vsmooth[1:, t_start:, t_start:], axis=0))
    )

    # E[f_{t-1}*f_{t-1}' | Omega_T]
    EZZ_BB = np.diag(
        np.diag(np.matmul(Zsmooth[t_start:, :-1], Zsmooth[t_start:, :-1].T))
    ) + np.diag(np.diag(np.sum(Vsmooth[:-1, t_start:, t_start:], axis=0)))

    # E[f_t*f_{t-1}' | Omega_T]
    EZZ_FB = np.diag(np.diag(np.matmul(Zsmooth[t_start:, 1:], Zsmooth[t_start:, :-1].T))) + np.diag(
        np.diag(np.sum(VVsmooth[:, t_start:, t_start:], axis=0))
    )

    A_i = np.matmul(EZZ_FB, np.diag(1 / np.diag(EZZ_BB)))  # Equation 6
    Q_i = (EZZ - np.matmul(A_i, EZZ_FB.T)) / T  # Equation 8

    # Place updated results in output matrix
    A_new[np.ix_(i_subset, i_subset)] = A_i[:niM, :niM].copy()
    Q_new[np.ix_(i_subset, i_subset)] = Q_i[:niM, :niM].copy()
    V_0_new[np.ix_(i_subset, i_subset)] = np.diag(np.diag(Vsmooth[0, i_subset, i_subset].copy()))

    # 3 MAXIMIZATION STEP (observation equation)
    Z_0 = Zsmooth[:, [0]].copy()

    # Set missing data series values to 0
    y = y.copy()
    nanY = np.isnan(y).astype(np.int64)
    y[np.isnan(y)] = 0

    # LOADINGS
    C_new = C.copy()

    # Blocks
    bl = np.unique(blocks, axis=0)  # Unique loadings
    n_bl = bl.shape[0]  # Number of unique loadings

    for i in range(num_blocks):  # Loop through each block
        if i == 0:
            # Initialize indices
            bl_idxQ = np.tile(bl[:, [i]], (1, r[0, i] * ppC))
            bl_idxM = np.hstack(
                [np.tile(bl[:, [i]], (1, r[0, i])), np.zeros((n_bl, r[0, i] * (ppC - 1)))]
            )
            R_con = np.kron(R_mat, np.eye(r[0, i]))
            q_con = np.zeros((r[0, i] * R_mat.shape[0], 1))
        else:
            # Indicator for monthly factor loadings
            bl_idxQ = np.hstack([bl_idxQ, np.tile(bl[:, [i]], (1, r[0, i] * ppC))])

            # Indicator for quarterly factor loadings
            bl_idxM = np.hstack(
                [
                    np.hstack([bl_idxM, np.tile(bl[:, [i]], (1, r[0, i]))]),
                    np.zeros((n_bl, r[0, i] * (ppC - 1))),
                ]
            )

            # Block diagonal matrix giving monthly-quarterly aggreg scheme
            R_con = block_diag(R_con, np.kron(R_mat, np.eye(r[0, i])))
            q_con = np.vstack([q_con, np.zeros((r[0, i] * R_mat.shape[0], 1))])

    #  Indicator for monthly/quarterly blocks in observation matrix
    bl_idxM = bl_idxM == 1
    bl_idxQ = bl_idxQ == 1

    i_idio_M = i_idio[:nM].copy()  # Gives 1 for monthly series
    n_idio_M = np.where(i_idio_M)[0].shape[0]  # Number of monthly series
    c_i_idio = np.cumsum(i_idio)  # Cumulative number of monthly series

    for i in range(n_bl):  # Loop through unique loadings (e.g. [1 0 0 0], [1 1 0 0])
        bl_i = bl[[i], :].copy()
        rs = np.sum(r[np.where(bl_i == 1)])  # Total num of blocks loaded
        idx_i = np.where((blocks == bl_i).all(axis=1))[0]  # Indices for bl_i
        idx_iM = idx_i[idx_i < nM]  # Only monthly
        n_i = len(idx_iM)  # Number of monthly series

        # Initialize sums in equation 13 of BGR 2010
        denom = np.zeros((n_i * rs, n_i * rs))
        nom = np.zeros((n_i, rs))

        # Stores monthly indices (done for input robustness)
        i_idio_i = i_idio_M[idx_iM, :].flatten("F").copy()
        i_idio_ii = c_i_idio[idx_iM].copy()
        i_idio_ii = i_idio_ii[i_idio_i].copy() - 1

        # UPDATE MONTHLY VARIABLES: Loop through each period ----------------
        bl_idxM_ind = np.where(bl_idxM[i, :])[0]

        for t in range(T):
            # Selection matrix (1 for nonmissing values)
            Wt = np.diag(np.logical_not(nanY[idx_iM, t]).astype(np.int64))

            # E[f_t*t_t' | Omega_T]
            denom += np.kron(
                np.matmul(Zsmooth[bl_idxM_ind][:, [t + 1]], Zsmooth[bl_idxM_ind][:, [t + 1]].T)
                + Vsmooth[t + 1][np.ix_(bl_idxM_ind, bl_idxM_ind)],
                Wt,
            )

            # E[y_t*f_t' | Omega_T]
            nom += np.matmul(y[idx_iM][:, [t]], Zsmooth[bl_idxM_ind][:, [t + 1]].T) - np.matmul(
                Wt[:, i_idio_i],
                np.matmul(Zsmooth[rp1 + i_idio_ii][:, [t + 1]], Zsmooth[bl_idxM_ind][:, [t + 1]].T)
                + Vsmooth[t + 1][rp1 + i_idio_ii, :][:, bl_idxM_ind],
            )

        # Eqn 13 BGR 2010
        vec_C = np.matmul(np.linalg.inv(denom), nom.flatten("F").reshape((-1, 1)))

        # Place updated monthly results in output matrix
        C_new[np.ix_(idx_iM, bl_idxM_ind)] = vec_C.copy().reshape((n_i, rs), order="F")

        # UPDATE QUARTERLY VARIABLES -----------------------------------------
        idx_iQ = idx_i[idx_i >= nM].copy()  # Index for quarterly series
        rps = rs * ppC

        # Monthly-quarterly aggregation scheme
        R_con_i = R_con[:, bl_idxQ[i, :]]
        q_con_i = q_con.copy()

        no_c = np.where(~(R_con_i.any(axis=1)))[0]
        R_con_i = np.delete(R_con_i, no_c, axis=0)
        q_con_i = np.delete(q_con_i, no_c, axis=0)

        # Loop through quarterly series in loading. Parallels the monthly code.
        for j in idx_iQ:
            # Initialization
            denom = np.zeros((rps, rps))
            nom = np.zeros((1, rps))

            idx_jQ = j - nM  # Ordinal position of quarterly variable
            # Loc of factor structure corresponding to quarterly var residuals
            i_idio_jQ = np.arange(rp1 + n_idio_M + 5 * (idx_jQ), rp1 + n_idio_M + 5 * (idx_jQ + 1))

            # Place quarterly values in output matrix
            V_0_new[np.ix_(i_idio_jQ, i_idio_jQ)] = Vsmooth[0][np.ix_(i_idio_jQ, i_idio_jQ)].copy()
            A_new[i_idio_jQ[0], i_idio_jQ[0]] = A_i[i_idio_jQ[0] - rp1, i_idio_jQ[0] - rp1].copy()
            Q_new[i_idio_jQ[0], i_idio_jQ[0]] = Q_i[i_idio_jQ[0] - rp1, i_idio_jQ[0] - rp1].copy()

            bl_idxQ_ind = np.where(bl_idxQ[i, :])[0]

            for t in range(T):
                # Selection matrix for quarterly values
                Wt = np.diag(np.logical_not(nanY[[j]][:, [t]]).astype(np.int64))

                # Intermediate steps in BGR equation 13
                denom += np.kron(
                    np.matmul(Zsmooth[bl_idxQ_ind][:, [t + 1]], Zsmooth[bl_idxQ_ind][:, [t + 1]].T)
                    + Vsmooth[t + 1][np.ix_(bl_idxQ_ind, bl_idxQ_ind)],
                    Wt,
                )
                nom += y[j, t] * Zsmooth[bl_idxQ_ind, t + 1].T
                nom -= np.matmul(
                    Wt,
                    np.matmul(
                        np.matmul(np.array([[1, 2, 3, 2, 1]]), Zsmooth[i_idio_jQ][:, [t + 1]]),
                        Zsmooth[bl_idxQ_ind][:, [t + 1]].T,
                    )
                    + np.matmul(
                        np.array([[1, 2, 3, 2, 1]]), Vsmooth[t + 1][np.ix_(i_idio_jQ, bl_idxQ_ind)]
                    ),
                )

            C_i = np.matmul(np.linalg.inv(denom), nom.T)

            # BGR equation 13
            C_i_constr = C_i - np.matmul(
                np.matmul(
                    np.matmul(np.linalg.inv(denom), R_con_i.T),
                    np.linalg.inv(np.matmul(np.matmul(R_con_i, np.linalg.inv(denom)), R_con_i.T)),
                ),
                np.matmul(R_con_i, C_i) - q_con_i,
            )

            # Place updated values in output structure
            C_new[j, bl_idxQ_ind] = C_i_constr.flatten("F")

    # 3B. UPDATE COVARIANCE OF RESIDUALS FOR OBSERVATION EQUATION -----------
    R_new = np.zeros((n, n))
    for t in range(T):
        # Selection matrix
        Wt = np.diag(np.logical_not(nanY[:, t])).astype(np.int64)

        # BGR equation 15
        R_new += (
            np.matmul(
                y[:, [t]] - np.matmul(np.matmul(Wt, C_new), Zsmooth[:, [t + 1]]),
                (y[:, [t]] - np.matmul(np.matmul(Wt, C_new), Zsmooth[:, [t + 1]])).T,
            )
            + np.matmul(
                np.matmul(np.matmul(np.matmul(Wt, C_new), Vsmooth[t + 1][:, :]), C_new.T), Wt
            )
            + np.matmul(np.matmul((np.eye(n) - Wt), R), (np.eye(n) - Wt))
        )

    i_idio_M = np.where(i_idio_M.flatten("F"))[0]
    R_new = R_new / T
    RR = np.diag(R_new).copy()  # RR(RR<1e-2) = 1e-2
    RR[i_idio_M] = 1e-4  # Ensure non-zero measurement error (Doz, Giannone, Reichlin 2012)
    RR[nM:] = 1e-4
    R_new = np.diag(RR).copy()
    return C_new, R_new, A_new, Q_new, Z_0, V_0, loglik


def em_converged(
    loglik: float, previous_loglik: float, threshold: float = 1e-4, check_decreased: int = 1
) -> tuple[int, int]:
    # em_converged    Checks whether the EM algorithm has converged.
    #   Convergence occurs if |f(t) - f(t-1)| / avg < threshold, where
    #   avg = (|f(t)| + |f(t-1)|)/2 and f(t) is log-lik at iteration t.

    # Initialize output
    converged = 0
    decrease = 0

    # Check if log-likelihood decreases (optional)
    if check_decreased == 1:
        if (loglik - previous_loglik) < -1e-3:
            print(f"******likelihood decreased from {previous_loglik} to {loglik}")
            decrease = 1

    # Check convergence criteria
    delta_loglik = np.abs(loglik - previous_loglik)  # Difference in loglik
    avg_loglik = (np.abs(loglik) + np.abs(previous_loglik) + np.finfo(float).eps) / 2

    if (delta_loglik / avg_loglik) < threshold:
        converged = 1  # Check convergence

    return converged, decrease


# endregion


# region Kalman filter & smoother
def runKF(
    Y: np.ndarray,
    A: np.ndarray,
    C: np.ndarray,
    Q: np.ndarray,
    R: np.ndarray,
    Z_0: np.ndarray,
    V_0: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    # runKF()    Applies Kalman filter and fixed-interval smoother.
    #   Y_t = C_t Z_t + e_t,  e_t ~ N(0, R);  Z_t = A Z_{t-1} + mu_t, mu_t ~ N(0, Q)

    S = SKF(Y, A, C, Q, R, Z_0, V_0)  # Kalman filter
    S = FIS(A, S)  # Fixed interval smoother

    # Organize output
    zsmooth = S["ZmT"].copy()
    Vsmooth = S["VmT"].copy()
    VVsmooth = S["VmT_1"].copy()
    loglik = S["loglik"].copy()

    return zsmooth, Vsmooth, VVsmooth, loglik


def SKF(
    Y: np.ndarray,
    A: np.ndarray,
    C: np.ndarray,
    Q: np.ndarray,
    R: np.ndarray,
    Z_0: np.ndarray,
    V_0: np.ndarray,
) -> dict:
    # SKF    Applies the Kalman filter.

    # INITIALIZE OUTPUT VALUES ---------------------------------------------
    m = C.shape[1]  # dimensions of state space matrix
    nobs = Y.shape[1]  # number of observations

    # Instantiate output
    S: dict = {}
    S["Zm"] = np.zeros((m, nobs))  # Z_t | t-1 (prior)
    S["Vm"] = np.zeros((nobs, m, m))  # V_t | t-1 (prior)
    S["ZmU"] = np.zeros((m, nobs + 1))  # Z_t | t (posterior/updated)
    S["VmU"] = np.zeros((nobs + 1, m, m))  # V_t | t (posterior/updated)
    S["loglik"] = 0

    # SET INITIAL VALUES ----------------------------------------------------
    S["Zm"][:] = np.nan
    S["Vm"][:] = np.nan
    S["ZmU"][:] = np.nan
    S["VmU"][:] = np.nan

    Zu = Z_0.copy()  # Z_0|0 (In below loop, Zu gives Z_t | t)
    Vu = V_0.copy()  # V_0|0 (In below loop, Vu gives V_t | t)

    # Store initial values
    S["ZmU"][:, [0]] = Zu.copy()
    S["VmU"][0, :, :] = Vu.copy()

    # KALMAN FILTER PROCEDURE ----------------------------------------------
    for t in range(nobs):
        # CALCULATING PRIOR DISTRIBUTION----------------------------------
        # Use transition eqn to create prior estimate for factor (Z = Z_t|t-1)
        Z = np.matmul(A, Zu)

        # Prior covariance matrix of Z (V = V_t|t-1) = A*Vu*A' + Q
        V = np.matmul(np.matmul(A, Vu), A.T) + Q
        V = 0.5 * (V + V.T)  # Trick to make symmetric

        # CALCULATING POSTERIOR DISTRIBUTION ----------------------------
        # Removes missing series: These are removed from Y, C, and R
        Y_t, C_t, R_t, _ = MissData(Y[:, [t]], C, R)

        # Check if y_t contains no data. If so, replace Zu and Vu with prior.
        if Y_t.shape[0] == 0:
            Zu = Z.copy()
            Vu = V.copy()
        else:
            # Var(c_t*Z_t + e_t) = c_t*V*c_t' + R
            VC = np.matmul(V, C_t.T)
            iF = np.linalg.inv(np.matmul(C_t, VC) + R_t)

            # Matrix of population regression coefficients (QuantEcon eqn #4)
            VCF = np.matmul(VC, iF)

            # Difference between actual and predicted observation matrix values
            innov = Y_t - np.matmul(C_t, Z)

            # Update estimate of factor values (posterior)
            Zu = Z + np.matmul(VCF, innov)

            # Update covariance matrix (posterior) for time t
            Vu = V - np.matmul(VCF, VC.T)
            Vu = 0.5 * (Vu + Vu.T)

            # Update log likelihood
            S["loglik"] = (
                S["loglik"]
                + 0.5 * (np.log(np.linalg.det(iF)) - np.matmul(np.matmul(innov.T, iF), innov))[0, 0]
            )

        # STORE OUTPUT----------------------------------------------------
        # Store covariance and observation values for t-1 (priors)
        S["Zm"][:, [t]] = Z.copy()
        S["Vm"][[t], :, :] = V.copy()

        # Store covariance and state values for t (posteriors)
        S["ZmU"][:, [t + 1]] = Zu.copy()
        S["VmU"][t + 1, :, :] = Vu.copy()

    # Store Kalman gain k_t
    if Y_t.shape[0] == 0:
        S["k_t"] = np.zeros((m, m))
    else:
        S["k_t"] = np.matmul(VCF, C_t)

    return S


def FIS(A: np.ndarray, S: dict) -> dict:
    # FIS()    Applies fixed-interval smoother (used with SKF()). See Harvey
    # (1990), 'Forecasting, structural time series models and the Kalman
    # filter', p. 154.

    # ORGANIZE INPUT ---------------------------------------------------------
    m, nobs = S["Zm"].shape
    S["ZmT"] = np.zeros((m, nobs + 1))
    S["VmT"] = np.zeros((nobs + 1, m, m))

    # Fill the final period of ZmT, VmT with SKF() posterior values
    S["ZmT"][:, nobs] = np.squeeze(S["ZmU"][:, nobs])
    S["VmT"][nobs, :, :] = np.squeeze(S["VmU"][nobs, :, :])

    # Initialize VmT_1 lag 1 covariance matrix for final period
    VmT_1_init = np.matmul(np.matmul(np.eye(m) - S["k_t"], A), np.squeeze(S["VmU"][nobs - 1, :, :]))
    S["VmT_1"] = np.zeros((nobs, VmT_1_init.shape[0], VmT_1_init.shape[1]))
    S["VmT_1"][nobs - 1, :, :] = VmT_1_init

    # Used for recursion process. See companion file for details
    J_2 = np.matmul(
        np.matmul(np.squeeze(S["VmU"][nobs - 1, :, :]), A.T),
        np.linalg.pinv(np.squeeze(S["Vm"][nobs - 1, :, :])),
    )

    # RUN SMOOTHING ALGORITHM ----------------------------------------------
    for t in range(nobs)[::-1]:  # Loop through time reverse-chronologically
        # Store posterior and prior factor covariance values
        VmU = np.squeeze(S["VmU"][t, :, :])
        Vm1 = np.squeeze(S["Vm"][t, :, :])

        # Store previous period smoothed factor covariance and lag-1 covariance
        V_T = np.squeeze(S["VmT"][t + 1, :, :])
        V_T1 = np.squeeze(S["VmT_1"][t, :, :])

        J_1 = J_2.copy()

        # Update smoothed factor estimate
        S["ZmT"][:, [t]] = S["ZmU"][:, [t]] + np.matmul(
            J_1, S["ZmT"][:, [t + 1]] - np.matmul(A, S["ZmU"][:, [t]])
        )

        # Update smoothed factor covariance matrix
        S["VmT"][t, :, :] = VmU + np.matmul(J_1, np.matmul((V_T - Vm1), J_1.T))

        if t > 0:
            # Update weight
            J_2 = np.matmul(
                np.matmul(np.squeeze(S["VmU"][t - 1, :, :]), A.T),
                np.linalg.pinv(np.squeeze(S["Vm"][t - 1, :, :])),
            )

            # Update lag 1 factor covariance matrix
            S["VmT_1"][t - 1, :, :] = np.matmul(VmU, J_2.T) + np.matmul(
                J_1, np.matmul(V_T1 - np.matmul(A, VmU), J_2.T)
            )
    return S


def MissData(
    y: np.ndarray, C: np.ndarray, R: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # MissData    Eliminates the rows in y and matrices C, R that correspond to
    # missing data (NaN) in y. L restores standard dimensions.

    # Returns 1 for nonmissing series
    ix = np.where(~np.isnan(y).flatten("F"))[0]

    # Index for columns with nonmissing variables
    e = np.eye(y.shape[0])
    L = e[:, ix].copy()

    # Removes missing series
    y = y[ix].copy()

    # Removes missing series from observation matrix
    C = C[ix, :].copy()

    # Removes missing series from transition matrix
    R = R[np.ix_(ix, ix)].copy()

    return y, C, R, L


# endregion
