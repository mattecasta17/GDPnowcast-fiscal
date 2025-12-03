import os
import numpy as np
import pandas as pd
from Functions.dfm import SKF

def extract_common_residual(X_new, Spec, Res, series, vintage, output_dir="common_residual_decomp"):
    """
    Calcola: GDP_common, GDP_residual (proxy = 0), quote.
    Allinea X_new a SKF: shape = (N_variabili, T_tempo), con N = Res["C"].shape[0].
    Salva CSV e ritorna (df, F_last).
    """
    os.makedirs(output_dir, exist_ok=True)

    # ---------- 1) Orientamento: righe = N variabili, colonne = T
    n_model = Res["C"].shape[0]
    if isinstance(X_new, pd.DataFrame):
        X_new = X_new.values

    if X_new.shape[0] == n_model:
        pass  # già corretto: (N, T)
    elif X_new.shape[1] == n_model:
        X_new = X_new.T
        print(f"Transposed X_new to (N,T): {X_new.shape}")
    else:
        raise ValueError(f"Impossibile allineare X_new a N={n_model}. Shape attuale: {X_new.shape}")

    if X_new.shape[0] > n_model:
        print(f"⚠️ X_new ha {X_new.shape[0]} variabili, il modello {n_model}. Tronco a {n_model}.")
        if hasattr(Spec, "SeriesID"):
            extra_vars = list(getattr(Spec, "SeriesID", []))[n_model:]
            if extra_vars:
                print(f"Variabili troncate: {extra_vars}")
        X_new = X_new[:n_model, :]

    # ---------- 2) Kalman filter → fattori
    res_skf = SKF(
        X_new,
        Res["A"],
        Res["C"],
        Res["Q"],
        Res["R"],
        Res["Z_0"],
        Res["V_0"]
    )

    # Estrai dal dizionario
    Z = res_skf.get("Zm")      # stati filtrati (fattori)
    V = res_skf.get("Pm")      # covarianze
    logL = res_skf.get("logL") # log-likelihood, se presente

    # Verifica orientamento dei fattori
    if Z.shape[0] <= Z.shape[1]:
        F_last = Z[:, -1]  # shape: (n_fattori,)
    else:
        F_last = Z[-1, :]  # fallback
    print(f"F_last shape: {F_last.shape}")

    # ---------- 3) Decomposizione GDP
    C = Res["C"]
    Wx = Res.get("Wx", None)
    Mx = Res.get("Mx", None)

    series_ids = getattr(Spec, "SeriesID", None)
    if isinstance(series_ids, (pd.Series, np.ndarray, list)):
        series_ids = np.array(series_ids)
    else:
        raise ValueError("Spec.SeriesID non disponibile o in formato inatteso.")

    gdp_idx = int(np.where(series_ids == series)[0][0])

    gdp_common = float(np.dot(C[gdp_idx, :], F_last))
    if Wx is not None and Mx is not None:
        gdp_common = gdp_common * Wx[gdp_idx] + Mx[gdp_idx]

    gdp_total = gdp_common
    gdp_resid = 0.0

    share_common = np.nan if gdp_total == 0 else gdp_common / gdp_total
    share_residual = np.nan if gdp_total == 0 else gdp_resid / gdp_total

    # ---------- 4) Salva
    df = pd.DataFrame([{
        "vintage": vintage,
        "GDP_total": gdp_total,
        "GDP_common": gdp_common,
        "GDP_residual": gdp_resid,
        "share_common": share_common,
        "share_residual": share_residual
    }])

    out_file = f"{output_dir}/gdp_common_residual_{vintage}.csv"
    df.to_csv(out_file, index=False)
    print(f"Saved {out_file}")

    return df, F_last





