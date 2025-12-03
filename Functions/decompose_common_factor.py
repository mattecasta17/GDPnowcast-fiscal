import os
import numpy as np
import pandas as pd

def decompose_common_factor(F_last, Spec, Res, series, vintage, X_new, output_dir="common_residual_decomp"):
    """
    Decompose GDP nowcast into:
      - common vs residual factors
      - and within the common factor: C, I, NX, G, Other (in GDP percentage points)
    """

    os.makedirs(output_dir, exist_ok=True)

    # -------------------------
    # Component mapping refined
    # -------------------------
    component_map = {
        # --- Consumption (C)
        "PCEC96": "C", "RSAFS": "C", "DSPIC96": "C", "PAYEMS": "C",
        "UNRATE": "C", "JTSJOL": "C",

        # --- Investment (I)
        "DGORDER": "I", "INDPRO": "I", "TTLCONS": "I", "HOUST": "I", "PERMIT": "I",
        "BUSINV": "I", "WHLSLRIMSA": "I", "TCU": "I",
        "AMDMVS": "I", "AMDMUO": "I", "AMDMTI": "I",
        "GACDISA066MSFRBNY": "I", "GACDFSA066MSFRBPHI": "I",

        # --- Net Exports (NX)
        "BOPTEXP": "NX", "BOPTIMP": "NX", "IR": "NX", "IQ": "NX",

        # --- Government (G)
        # Usa solo se hai spesa pubblica esplicita
        # "GCEC1": "G",

        # --- Other (prezzi, costi, indicatori generali)
        "CPIAUCSL": "Other", "PPIFIS": "Other", "CPILFESL": "Other", "PCEPILFE": "Other", "PCEPI": "Other",
        "ULCNFB": "Other", "A261RX1Q020SBEA": "Other"
        # NOTA: GDPC1 non incluso → evita autoreferenzialità
    }

    # -------------------------
    # Estrai dati dal modello
    # -------------------------
    C = Res["C"]  # Loadings (N x r)
    gdp_idx = np.where(Spec.SeriesID == series)[0][0]
    GDP_common = np.dot(C[gdp_idx, :], F_last)
    X_last = X_new[-1, gdp_idx]
    GDP_resid = X_last - GDP_common
    GDP_total = X_last

    # -------------------------
    # Decomposizione fattore comune
    # -------------------------
    weights = []
    for i, var in enumerate(Spec.SeriesID):
        if var == series:
            continue  # esclude GDPC1
        comp = component_map.get(var, "Other")
        w = float(np.dot(C[gdp_idx, :], C[i, :]))  # proxy di correlazione con GDP
        weights.append((comp, w))

    dfw = pd.DataFrame(weights, columns=["Component", "Weight"])
    comp_w = dfw.groupby("Component", as_index=False)["Weight"].sum()
    total_w = comp_w["Weight"].sum()
    comp_w["share_common"] = comp_w["Weight"] / total_w if total_w != 0 else 0.0

    # contributo in punti percentuali di GDP
    comp_w["pp_contribution"] = comp_w["share_common"] * GDP_common
    comp_w = comp_w[["Component", "pp_contribution", "share_common"]]

    # -------------------------
    # Output finale
    # -------------------------
    df_summary = pd.DataFrame([{
        "Quarter": vintage,
        "GDP_total": GDP_total,
        "GDP_common": GDP_common,
        "GDP_residual": GDP_resid
    }])

    df_result = df_summary.assign(key=1).merge(comp_w.assign(key=1), on="key").drop("key", axis=1)
    save_path = f"{output_dir}/gdp_common_residual_{vintage}.csv"
    df_result.to_csv(save_path, index=False)
    print(f"Saved decomposition → {save_path}")

    return df_result


