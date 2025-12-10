#------------------------------------------------- Libraries
import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px


#------------------------------------------------- Config
st.set_page_config(page_title="GDP Nowcast Dashboard w/ Fiscal", layout="wide")

NOWCAST_DIR = "nowcast_Q_fiscal"
METRICS_DIR = "metrics_Q_fiscal"

#------------------------------------------------- Detect files
quarters = sorted([
    f.replace("nowcast_", "").replace("_fiscal.csv", "")
    for f in os.listdir(NOWCAST_DIR)
    if f.startswith("nowcast_") and f.endswith(".csv")
])

years = sorted(set(q.split("_")[0] for q in quarters))

#------------------------------------------------- Variable dictionary (updated from screenshot)
variable_dict = {
    "BOPTEXP": "Exports",  # trade
    "BOPTIMP": "Imports",  # trade
    "BUSINV": "Business Inventories",  # production
    "CPIAUCSL": "Consumer Price Index (All Urban Consumers, SA)",  # price
    "CPILFESL": "CPI Less Food & Energy (Core CPI)",  # price
    "DGORDER": "Durable Goods Orders",  # production
    "DSPI96": "Disposable Personal Income (Real, Chained 2017 USD)",  # income
    "GACDFSA066MSFRBPHI": "Philadelphia Fed Mfg Index",  # survey
    "GDPC1": "Real Gross Domestic Product (Chained 2017 USD)",
    "HOUST": "Housing Starts (Total, SAAR)",  # construction
    "INDPRO": "Industrial Production Index",  # production
    "IQ": "Export Price Index",  # trade
    "IR": "Import Price Index",  # trade
    "JTSJOL": "Job Openings (JOLTS)",  # labor
    "PAYEMS": "All Employees: Total Nonfarm Payrolls",  # labor
    "PCE96": "Real Personal Consumption Expenditures",  # consumption
    "PCEPI": "PCE Price Index (Headline PCE)",  # price
    "PCEPILFE": "PCE Price Index Excluding Food & Energy (Core PCE)",  # price
    "PERMIT": "Building Permits",  # construction
    "RSAFS": "Retail Sales: Advance Monthly Sales",  # consumption
    "TCU": "Capacity Utilization Rate",  # production
    "TTLCONS": "Construction Spending",  # construction
    "ULCNFB": "Unit Labor Costs: Nonfarm Business Sector",  # labor
    "UNRATE": "Civilian Unemployment Rate",  # labor
    "AMDMVS": "Manufacturer’s Shipments: Durable Goods",  # production
    "AMDMUO": "Manufacturers’ Unfilled Orders: All Industries",  # production
    "AMDMTI": "Manufacturers’ Inventories: Durable Goods",  # production
    "GACDISA066MSFRBNY": "Empire State Mfg Index",  # surveys
    "GCEC1": "Real Government Consumption Expenditures and Gross Investment",
    "MTSDS133FMS": "Federal Surplus or Deficit [-]",
    "W875RX1": "Real personal income excluding current transfer receipts",
}

# --- FED-STYLE CATEGORY MAPPING ---
fed_category_map = {
    "PCE96": "Consumption",
    "RSAFS": "Consumption",
    "DSPI96": "Income",
    "PAYEMS": "Labor",
    "UNRATE": "Labor",
    "JTSJOL": "Labor",
    "ULCNFB": "Labor",
    "DGORDER": "Production",
    "INDPRO": "Production",
    "TCU": "Production",
    "AMDMVS": "Production",
    "AMDMUO": "Production",
    "AMDMTI": "Production",
    "BUSINV": "Production",
    "BOPTEXP": "Trade",
    "BOPTIMP": "Trade",
    "IQ": "Trade",
    "IR": "Trade",
    "GACDFSA066MSFRBPHI": "Surveys",
    "GACDISA066MSFRBNY": "Surveys",
    "CPIAUCSL": "Prices",
    "CPILFESL": "Prices",
    "PCEPI": "Prices",
    "PCEPILFE": "Prices",
    "HOUST": "Construction",
    "PERMIT": "Construction",
    "TTLCONS": "Consumption",
    "GCEC1": "Fiscal",
    "MTSDS133FMS": "Fiscal",
    "W875RX1": "Fiscal",
}

fed_colors = {
    "Consumption": "#009E73",
    "Production": "#0072B2",
    "Construction": "#D55E00",
    "Labor": "#E69F00",
    "Income": "#F0E442",
    "Prices": "#999999",
    "Trade": "#56B4E9",
    "Surveys": "#CC79A7",
    "Other": "#BBBBBB",
    "Fiscal": "#8A2BE2"
}

#------------------------------------------------- Sidebar
st.sidebar.title("Nowcast Dashboard w/Fiscal")
view_mode = st.sidebar.radio("View mode:", ["Single Quarter", "Multi Quarter", "Multi Year"])

st.markdown("---")
st.header("Metrics Explanation")
st.write("""
- **RMSE (Root Mean Squared Error):** Average magnitude of forecast errors (penalizes big errors more).
- **MAE (Mean Absolute Error):** Average absolute difference between nowcast and actual GDP.
- **Bias:** Average signed error. Positive = systematic overestimation, Negative = underestimation.
- **Impact from Revisions:** Effect of statistical revisions to already published data.
- **Impact from Releases:** Effect of new incoming data releases.
- **Variance:** Measures stability of forecasts across vintages (higher = more volatile).
""")

#================================================= Single Quarter
if view_mode == "Single Quarter":
    selected_year = st.sidebar.selectbox("Select Year", years)
    year_quarters = [q for q in quarters if q.startswith(selected_year + "_")]
    selected_q = st.sidebar.selectbox("Select Quarter", year_quarters)

    nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{selected_q}_fiscal.csv")
    metrics_file = os.path.join(METRICS_DIR, f"metrics_{selected_q}_fiscal.csv")

    if not (os.path.exists(nowcast_file) and os.path.exists(metrics_file)):
        st.warning("Missing files for the selected quarter.")
        st.stop()

    df_nowcast = pd.read_csv(nowcast_file)
    df_metrics = pd.read_csv(metrics_file)
    df_nowcast["Week"] = range(1, len(df_nowcast) + 1)
    gdp_actual = df_nowcast["y_new"].iloc[-1] + df_nowcast["error"].iloc[-1]

    st.header(f"Summary Metrics – {selected_q}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("RMSE", f"{df_metrics['RMSE'].iloc[0]:.3f}")
    col2.metric("MAE", f"{df_metrics['MAE'].iloc[0]:.3f}")
    col3.metric("Bias", f"{df_metrics['Bias'].iloc[0]:.3f}")


    st.subheader("Nowcast Evolution")
    fig, ax = plt.subplots(figsize=(16,5))
    ax.plot(df_nowcast["Week"], df_nowcast["y_new"], marker="o", label="Nowcast")
    ax.scatter(df_nowcast["Week"].iloc[-1], gdp_actual, marker="s", s=90,
               facecolor="white", edgecolor="black", label="Advance GDP Estimate")
    ax.set_xlabel("Week")
    ax.set_ylabel("GDP Growth (%)")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Error Evolution")
    fig, ax = plt.subplots(figsize=(16,5))
    ax.plot(df_nowcast["Week"], df_nowcast["error"], marker="o", color="blue", label="Error (signed)")
    ax.plot(df_nowcast["Week"], df_nowcast["abs_error"], marker="x", color="orange", alpha=0.7, label="Abs Error")
    ax.set_xlabel("Week")
    ax.set_ylabel("Error")
    ax.legend()
    st.pyplot(fig)

    mean_err = df_nowcast["error"].mean()
    share_pos = (df_nowcast["error"] > 0).mean()
    share_neg = (df_nowcast["error"] < 0).mean()
    st.caption(f"Average bias: {mean_err:.3f} (positive={share_pos:.0%}, negative={share_neg:.0%}).")

    st.subheader("Impact Decomposition")
    fig, ax = plt.subplots(figsize=(16,5))
    ax.bar(df_nowcast["Week"], df_nowcast["impact_revisions"], label="Revisions")
    ax.bar(df_nowcast["Week"], df_nowcast["impact_releases"],
           bottom=df_nowcast["impact_revisions"], label="Releases")
    ax.set_xlabel("Week")
    ax.set_ylabel("Impact")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Variable Codes Legend")
    legend_df = pd.DataFrame(list(variable_dict.items()), columns=["Code", "Full Name"])
    st.dataframe(legend_df)

    # === VARIABLE-LEVEL IMPACT ===
    st.subheader("Variable-Level Impact")
    st.caption(
        "This bar chart shows the total impact of each variable on the nowcast for the selected quarter. "
        "Positive bars indicate variables whose data releases or revisions pushed the GDP forecast upward, "
        "while negative bars represent variables that lowered the forecast. "
        "The length of each bar reflects the relative importance of that variable in explaining forecast changes."
    )
    news_file = f"news_Q_fiscal/news_{selected_q}_fiscal.xlsx"
    if os.path.exists(news_file):
        excel_news = pd.read_excel(news_file, sheet_name=None)
        impacts = []
        for week_name, df_news in excel_news.items():  # <--- Sheet name = week
            if df_news.columns[0] != "Variable":
                df_news = df_news.rename(columns={df_news.columns[0]: "Variable"})
            df_news["Week"] = week_name  # <--- Crucial addition
            impacts.append(df_news)
        if impacts:
            df_impacts = pd.concat(impacts, ignore_index=True)
            impact_by_var = df_impacts.groupby("Variable")["Impact"].sum().sort_values(ascending=False)
            st.bar_chart(impact_by_var)

            st.subheader("Heatmap of Variable Impacts during the Quarter")
            pivot_impacts = df_impacts.pivot(index="Variable", columns="Week", values="Impact")
            fig, ax = plt.subplots(figsize=(14, 6))
            sns.heatmap(pivot_impacts, cmap="RdYlGn", center=0,
                        annot=True, fmt=".2f", cbar_kws={'label': 'Impact'}, ax=ax)
            ax.set_xlabel("Week")
            ax.set_ylabel("Variable")
            st.pyplot(fig)
    else:
        st.warning(f"No news file found for {selected_q}")

    # === IMPACT BY CATEGORY (Fed logic) ===
    # Read sheets in the order they appear in the file
    xls = pd.ExcelFile(news_file)
    sheet_order = xls.sheet_names  # vintage order as in Excel

    # Build df_impacts preserving the order
    impacts = []
    for i, sh in enumerate(sheet_order):
        df_news = xls.parse(sh)
        if df_news.columns[0] != "Variable":
            df_news = df_news.rename(columns={df_news.columns[0]: "Variable"})
        df_news["Vintage"] = sh  # label X
        df_news["VintageIdx"] = i  # index for ordering
        impacts.append(df_news)

    df_impacts = pd.concat(impacts, ignore_index=True)

    # Map Fed category
    df_impacts["Category"] = df_impacts["Variable"].map(fed_category_map).fillna("Other")

    # Aggregate by vintage and category
    impact_by_week_cat = (
        df_impacts.groupby(["Vintage", "VintageIdx", "Category"], as_index=False)["Impact"]
        .sum()
    )

    # Categorical ordering on x-axis matches sheet order
    impact_by_week_cat["Vintage"] = pd.Categorical(
        impact_by_week_cat["Vintage"], categories=sheet_order, ordered=True
    )

    # Plot
    st.subheader("Weekly Impact by Category")
    fig = px.bar(
        impact_by_week_cat.sort_values("VintageIdx"),
        x="Vintage",
        y="Impact",
        color="Category",
        color_discrete_map=fed_colors,
        title="Impact of Data Releases (Fed-style view)",
    )
    fig.update_xaxes(type="category")  # force category axis
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Forecast Stability")
    fig, ax = plt.subplots(figsize=(16,5))
    ax.plot(df_nowcast["Week"], df_nowcast["variance_so_far"], marker="o", label="Variance")
    ax.set_xlabel("Week")
    ax.set_ylabel("Variance")
    st.pyplot(fig)

    st.subheader("Weekly Detail Table")
    st.dataframe(df_nowcast)


#================================================= Multi Quarter
elif view_mode == "Multi Quarter":
    st.header("Multi-Quarter Comparison")
    selected_multi_year = st.sidebar.selectbox("Select Year for Multi-Quarter view", years)
    quarters_to_plot = [q for q in quarters if q.startswith(selected_multi_year + "_")]

    all_dfs, metrics_list = [], []
    for q in quarters_to_plot:
        nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv")
        metrics_file = os.path.join(METRICS_DIR, f"metrics_{q}_fiscal.csv")
        if os.path.exists(nowcast_file) and os.path.exists(metrics_file):
            df = pd.read_csv(nowcast_file)
            df["date"] = pd.date_range(start=f"{selected_multi_year}-01-01", periods=len(df), freq="W")
            df["quarter"] = q
            all_dfs.append(df)
            m = pd.read_csv(metrics_file)
            m["quarter"] = q
            metrics_list.append(m)

    if not all_dfs:
        st.info("No data available for the selected year.")
        st.stop()

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_metrics_all = pd.concat(metrics_list, ignore_index=True)

    st.subheader(f"KPI Metrics – {selected_multi_year}")

    # Remove MPE column
    df_metrics_all = df_metrics_all.drop(columns=["MPE"], errors="ignore")

    # Convert to long format
    df_long = df_metrics_all.melt(id_vars="quarter", var_name="Metric", value_name="Value")

    # Bar chart with quarters on x-axis
    fig, ax = plt.subplots(figsize=(16, 5))
    sns.barplot(data=df_long, x="quarter", y="Value", hue="Metric", ax=ax, width=0.4)
    ax.axhline(0, color="red", linestyle="--")
    ax.set_title(f"KPI Metrics – {selected_multi_year}")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Value")
    st.pyplot(fig)

    import matplotlib.dates as mdates
    from pandas.tseries.offsets import MonthEnd

    st.subheader("Nowcast Evolution by Quarter (continuous timeline)")


    # function to find last Friday of a specific month
    def last_friday(year, month):
        # take last day of the month and go back until reaching Friday
        d = pd.to_datetime(f"{year}-{month}-01") + MonthEnd(0)
        while d.weekday() != 4:  # 4 = Friday
            d -= pd.Timedelta(days=1)
        return d


    # define periods for each quarter
    q_periods = {
        "q1": (last_friday(int(selected_multi_year) - 1, 11), last_friday(int(selected_multi_year), 4)),
        "q2": (last_friday(int(selected_multi_year), 2), last_friday(int(selected_multi_year), 7)),
        "q3": (last_friday(int(selected_multi_year), 5), last_friday(int(selected_multi_year), 10)),
        "q4": (last_friday(int(selected_multi_year), 8), last_friday(int(selected_multi_year) + 1, 1))
    }

    fig, ax = plt.subplots(figsize=(12, 6))

    for q in quarters_to_plot:
        df_q = pd.read_csv(os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv"))

        # determine which quarter
        qname = q.split("_")[1]  # e.g. 2017_q1 → "q1"

        start, end = q_periods[qname]
        fridays = pd.date_range(start=start, periods=len(df_q), freq="W-FRI")
        df_q["date"] = fridays

        # continuous line of the nowcast
        ax.plot(df_q["date"], df_q["y_new"], label=q)

        # square point = actual value (advance release = last observation)
        gdp_actual = df_q["y_new"].iloc[-1] + df_q["error"].iloc[-1]
        ax.scatter(df_q["date"].iloc[-1], gdp_actual,
                   marker="s", s=90, facecolor="white", edgecolor="black",
                   label=f"Advance GDP Estimate {q}")

    ax.set_title(f"Nowcast Evolution – {selected_multi_year}")
    ax.set_xlabel("Time")
    ax.set_ylabel("GDP Growth (%)")
    ax.legend()

    # X-axis always from November t-1 to January t+1
    x_start = last_friday(int(selected_multi_year) - 1, 11)
    x_end = last_friday(int(selected_multi_year) + 1, 1)
    ax.set_xlim([x_start, x_end])

    # Tick every 2 months
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()

    st.pyplot(fig)

    # =========================================
    # === MULTI QUARTER IMPACT BY CATEGORY ====
    # =========================================

    st.header("Cumulative Impact by Category – Multi Quarter View")

    all_quarter_impacts = []

    # 1) Loop only over the quarters of the selected year
    for q in quarters_to_plot:
        news_file = f"news_Q_fiscal/news_{q}_fiscal.xlsx"
        if not os.path.exists(news_file):
            continue

        xls = pd.ExcelFile(news_file)
        sheet_order = xls.sheet_names
        impacts = []

        for sheet in sheet_order:
            df_news = pd.read_excel(news_file, sheet_name=sheet)
            if df_news.columns[0] != "Variable":
                df_news = df_news.rename(columns={df_news.columns[0]: "Variable"})
            df_news["Vintage"] = sheet
            impacts.append(df_news)

        if impacts:
            df_q = pd.concat(impacts, ignore_index=True)
            df_q["Category"] = df_q["Variable"].map(fed_category_map).fillna("Other")

            # 2) Sum impacts per category within the quarter
            df_q_agg = (
                df_q.groupby("Category", as_index=False)["Impact"]
                .sum()
                .assign(Quarter=q)
            )
            all_quarter_impacts.append(df_q_agg)

    # 3) Merge all quarters of the selected year
    if all_quarter_impacts:
        df_multiq = pd.concat(all_quarter_impacts, ignore_index=True)

        # 4) Sort quarters (e.g. 2023_q1, 2023_q2, 2023_q3, 2023_q4)
        df_multiq["Quarter"] = pd.Categorical(
            df_multiq["Quarter"],
            categories=sorted(df_multiq["Quarter"].unique()),
            ordered=True
        )

        # 5) Stacked bar chart by quarter
        fig = px.bar(
            df_multiq,
            x="Quarter",
            y="Impact",
            color="Category",
            color_discrete_map=fed_colors,
            title=f"Cumulative GDP Impact by Category – {selected_multi_year}",
            barmode="stack"
        )
        fig.update_xaxes(title="Quarter")
        fig.update_yaxes(title="Cumulative Impact on GDP Nowcast")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"No impact data available for {selected_multi_year}.")

    st.subheader("Final Error per Quarter")

    # Select last value of each quarter
    final_err = df_all.groupby("quarter").tail(1)[["quarter", "error", "abs_error"]]

    # Convert to long format
    df_long = final_err.melt(id_vars="quarter", var_name="Type", value_name="Value")

    # Combined bar chart
    fig, ax = plt.subplots(figsize=(16, 5))
    sns.barplot(data=df_long, x="quarter", y="Value", hue="Type", ax=ax, width=0.4)
    ax.axhline(0, color="red", linestyle="--")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Error")
    ax.set_title("Final Error per Quarter")
    st.pyplot(fig)

    st.subheader("Absolute Error Trajectory by Quarter")
    fig, ax = plt.subplots(figsize=(16,6))
    for q in quarters_to_plot:
        df_q = df_all[df_all["quarter"] == q]
        ax.plot(df_q["date"], df_q["abs_error"], marker="o", label=q)
    ax.axhline(0, color="red", linestyle="--")
    ax.legend()
    st.pyplot(fig)


#================================================= Multi Year
else:
    st.header("Multi-Year Comparison")

    all_metrics, final_points, vol_points, rel_rev, all_impacts = [], [], [], [], []

    # --------- BUILD GLOBAL DATAFRAMES (nowcast, metrics, impacts) ----------
    for q in quarters:
        year = q.split("_")[0]
        nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv")
        metrics_file = os.path.join(METRICS_DIR, f"metrics_{q}_fiscal.csv")
        if not (os.path.exists(nowcast_file) and os.path.exists(metrics_file)):
            continue

        # metrics per quarter
        m = pd.read_csv(metrics_file)
        m["quarter"] = q
        m["year"] = year
        all_metrics.append(m)

        # nowcast per quarter
        df = pd.read_csv(nowcast_file)
        df["year"] = year
        df["quarter"] = q
        df["week"] = range(1, len(df) + 1)

        last = df.iloc[-1]
        final_points.append({
            "year": year,
            "quarter": q,
            "final_error": last["error"],
            "final_abs_error": last["abs_error"]
        })
        vol_points.append({
            "year": year,
            "quarter": q,
            "final_variance": last["variance_so_far"]
        })
        rel_rev.append({
            "year": year,
            "quarter": q,
            "releases": df["impact_releases"].sum(),
            "revisions": df["impact_revisions"].sum()
        })

        # variable-level impacts (for Top 10)
        news_file = f"news_Q_fiscal/news_{q}_fiscal.xlsx"
        if os.path.exists(news_file):
            xls = pd.ExcelFile(news_file)
            impacts_q = []
            for sheet in xls.sheet_names:
                df_news = xls.parse(sheet)
                if df_news.columns[0] != "Variable":
                    df_news = df_news.rename(columns={df_news.columns[0]: "Variable"})
                df_news["quarter"] = q
                df_news["year"] = year
                impacts_q.append(df_news[["Variable", "Impact", "quarter", "year"]])
            if impacts_q:
                all_impacts.append(pd.concat(impacts_q, ignore_index=True))

    if not all_metrics:
        st.info("No data available.")
        st.stop()

    metrics_all = pd.concat(all_metrics, ignore_index=True)
    finals = pd.DataFrame(final_points)
    vols = pd.DataFrame(vol_points)
    rr = pd.DataFrame(rel_rev)

    # -------------------------------------------------
    st.subheader("Nowcast Evolution – All Quarters (2017–2025, excluding 2020)")

    fig, ax = plt.subplots(figsize=(14, 7))

    from pandas.tseries.offsets import MonthEnd
    import matplotlib.dates as mdates

    def last_friday(year, month):
        d = pd.to_datetime(f"{year}-{month}-01") + MonthEnd(0)
        while d.weekday() != 4:  # 4 = Friday
            d -= pd.Timedelta(days=1)
        return d

    for q in quarters:
        year_str, qname = q.split("_")
        year = int(year_str)

        if year == 2020:
            continue

        q_periods = {
            "q1": (last_friday(year - 1, 11), last_friday(year, 4)),
            "q2": (last_friday(year, 2), last_friday(year, 7)),
            "q3": (last_friday(year, 5), last_friday(year, 10)),
            "q4": (last_friday(year, 8), last_friday(year + 1, 1)),
        }

        if qname not in q_periods:
            continue

        start, end = q_periods[qname]
        nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv")
        if not os.path.exists(nowcast_file):
            continue

        df_q = pd.read_csv(nowcast_file)
        if df_q.empty:
            continue

        fridays = pd.date_range(start=start, periods=len(df_q), freq="W-FRI")
        df_q["date"] = fridays

        ax.plot(df_q["date"], df_q["y_new"], label=q)

        gdp_actual = df_q["y_new"].iloc[-1] + df_q["error"].iloc[-1]
        ax.scatter(
            df_q["date"].iloc[-1],
            gdp_actual,
            marker="s",
            s=90,
            facecolor="white",
            edgecolor="black",
        )

    ax.set_title("Nowcast Evolution – All Quarters (2017–2025, excluding 2020)")
    ax.set_xlabel("Time")
    ax.set_ylabel("GDP Growth (%)")
    ax.set_xlim([pd.to_datetime("2016-11-25"), pd.to_datetime("2025-07-31")])
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    st.pyplot(fig)

    # --------------------- 2017–2019 ---------------------
    st.subheader("Nowcast Evolution – 2017 to 2019")

    fig1, ax1 = plt.subplots(figsize=(14, 6))

    for q in quarters:
        year_str, qname = q.split("_")
        year = int(year_str)

        if year < 2017 or year > 2019:
            continue

        q_periods = {
            "q1": (last_friday(year - 1, 11), last_friday(year, 4)),
            "q2": (last_friday(year, 2), last_friday(year, 7)),
            "q3": (last_friday(year, 5), last_friday(year, 10)),
            "q4": (last_friday(year, 8), last_friday(year + 1, 1)),
        }

        if qname not in q_periods:
            continue

        start, end = q_periods[qname]
        nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv")
        if not os.path.exists(nowcast_file):
            continue

        df_q = pd.read_csv(nowcast_file)
        if df_q.empty:
            continue

        fridays = pd.date_range(start=start, periods=len(df_q), freq="W-FRI")
        df_q["date"] = fridays

        ax1.plot(df_q["date"], df_q["y_new"], label=q)

        gdp_actual = df_q["y_new"].iloc[-1] + df_q["error"].iloc[-1]
        ax1.scatter(
            df_q["date"].iloc[-1],
            gdp_actual,
            marker="s",
            s=70,
            facecolor="white",
            edgecolor="black",
        )

    ax1.set_title("Nowcast Evolution – 2017 to 2019")
    ax1.set_xlim([pd.to_datetime("2016-11-25"), pd.to_datetime("2020-02-28")])
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig1.autofmt_xdate()
    ax1.legend(ncol=3, fontsize=7)
    st.pyplot(fig1)

    # --------------------- 2021–2025 ---------------------
    st.subheader("Nowcast Evolution – 2021 to 2025")

    fig2, ax2 = plt.subplots(figsize=(14, 6))

    for q in quarters:
        year_str, qname = q.split("_")
        year = int(year_str)

        if year < 2021 or year > 2025:
            continue

        q_periods = {
            "q1": (last_friday(year - 1, 11), last_friday(year, 4)),
            "q2": (last_friday(year, 2), last_friday(year, 7)),
            "q3": (last_friday(year, 5), last_friday(year, 10)),
            "q4": (last_friday(year, 8), last_friday(year + 1, 1)),
        }

        if qname not in q_periods:
            continue

        start, end = q_periods[qname]
        nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv")
        if not os.path.exists(nowcast_file):
            continue

        df_q = pd.read_csv(nowcast_file)
        if df_q.empty:
            continue

        fridays = pd.date_range(start=start, periods=len(df_q), freq="W-FRI")
        df_q["date"] = fridays

        ax2.plot(df_q["date"], df_q["y_new"], label=q)

        gdp_actual = df_q["y_new"].iloc[-1] + df_q["error"].iloc[-1]
        ax2.scatter(
            df_q["date"].iloc[-1],
            gdp_actual,
            marker="s",
            s=70,
            facecolor="white",
            edgecolor="black",
        )

    ax2.set_title("Nowcast Evolution – 2021 to 2025")
    ax2.set_xlim([pd.to_datetime("2020-11-25"), pd.to_datetime("2025-07-31")])
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig2.autofmt_xdate()
    ax2.legend(ncol=3, fontsize=7)
    st.pyplot(fig2)

    # -------------------------------------------------
    st.subheader("Final Nowcast vs BEA Advance Release (2017–2025, excl. 2020)")

    # Prepare storage
    final_nowcasts = []
    bea_values = []
    quarters_list = []
    dates_list = []

    for q in quarters:
        year_str, qname = q.split("_")
        year = int(year_str)

        nowcast_file = os.path.join(NOWCAST_DIR, f"nowcast_{q}_fiscal.csv")
        if not os.path.exists(nowcast_file):
            continue

        df_q = pd.read_csv(nowcast_file)
        if df_q.empty:
            continue

        # final nowcast
        final_nowcast = df_q["y_new"].iloc[-1]

        # BEA advance
        bea_adv = df_q["y_new"].iloc[-1] + df_q["error"].iloc[-1]

        # symbolic quarterly date
        if qname == "q1":
            quarter_date = pd.to_datetime(f"{year}-04-01") + MonthEnd(0)
        elif qname == "q2":
            quarter_date = pd.to_datetime(f"{year}-07-01") + MonthEnd(0)
        elif qname == "q3":
            quarter_date = pd.to_datetime(f"{year}-10-01") + MonthEnd(0)
        else:  # q4
            quarter_date = pd.to_datetime(f"{year + 1}-01-01") + MonthEnd(0)

        dates_list.append(quarter_date)
        quarters_list.append(q)
        final_nowcasts.append(final_nowcast)
        bea_values.append(bea_adv)

    # Build dataframe
    df_compare = pd.DataFrame({
        "Quarter": quarters_list,
        "Date": dates_list,
        "Nowcast_Final": final_nowcasts,
        "BEA_Advance": bea_values
    }).sort_values("Date")

    # Insert a gap for all quarters labelled 2020_q*
    mask_2020 = df_compare["Quarter"].str.startswith("2020_")
    df_compare.loc[mask_2020, ["Nowcast_Final", "BEA_Advance"]] = float("nan")

    # Plot
    fig3, ax3 = plt.subplots(figsize=(14, 6))

    ax3.plot(
        df_compare["Date"],
        df_compare["Nowcast_Final"],
        marker="o",
        linewidth=2.2,
        label="Final Nowcast"
    )

    ax3.plot(
        df_compare["Date"],
        df_compare["BEA_Advance"],
        marker="s",
        linewidth=2.2,
        label="BEA Advance Release"
    )

    ax3.set_title("Final Nowcast vs BEA Advance Release (2017–2025, excl. 2020)")
    ax3.set_xlabel("Time")
    ax3.set_ylabel("GDP Growth (%)")

    ax3.xaxis.set_major_locator(mdates.YearLocator())
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax3.legend()
    ax3.grid(True, alpha=0.2)

    st.pyplot(fig3)


    # -------------------------------------------------
    # === IMPACT BY CATEGORY (Fed logic) – MULTI YEAR ===
    st.subheader("Cumulative Impact by Category (Multi-Year Fed-style View)")

    all_year_impacts = []

    for y in years:
        yearly_quarters = [f"{y}_q1", f"{y}_q2", f"{y}_q3", f"{y}_q4"]
        all_quarter_impacts = []
        for q in yearly_quarters:
            news_file = f"news_Q_fiscal/news_{q}_fiscal.xlsx"
            if not os.path.exists(news_file):
                continue
            xls = pd.ExcelFile(news_file)
            sheet_order = xls.sheet_names
            impacts_yq = []
            for sheet in sheet_order:
                df_news = pd.read_excel(news_file, sheet_name=sheet)
                if df_news.columns[0] != "Variable":
                    df_news = df_news.rename(columns={df_news.columns[0]: "Variable"})
                df_news["Vintage"] = sheet
                impacts_yq.append(df_news)
            if impacts_yq:
                df_q = pd.concat(impacts_yq, ignore_index=True)
                df_q["Category"] = df_q["Variable"].map(fed_category_map).fillna("Other")
                df_q_agg = (
                    df_q.groupby("Category", as_index=False)["Impact"]
                    .sum()
                    .assign(Quarter=q)
                )
                all_quarter_impacts.append(df_q_agg)

        if all_quarter_impacts:
            df_y = pd.concat(all_quarter_impacts, ignore_index=True)
            df_y_agg = (
                df_y.groupby("Category", as_index=False)["Impact"]
                .sum()
                .assign(Year=y)
            )
            all_year_impacts.append(df_y_agg)

    if all_year_impacts:
        df_multi_year = pd.concat(all_year_impacts, ignore_index=True)
        df_multi_year["Year"] = pd.Categorical(
            df_multi_year["Year"],
            categories=sorted(df_multi_year["Year"].unique()),
            ordered=True,
        )

        fig = px.bar(
            df_multi_year,
            x="Year",
            y="Impact",
            color="Category",
            color_discrete_map=fed_colors,
            title="Cumulative GDP Impact by Category per Year",
            barmode="stack",
        )
        fig.update_xaxes(title="Year")
        fig.update_yaxes(title="Cumulative Impact on GDP Nowcast")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No impact data available for the selected years.")

    # ============================================================
    # === STATIC BAR CHART: CUMULATIVE IMPACT OF FISCAL CATEGORY ===
    # ============================================================

    import matplotlib.pyplot as plt

    # 1. Filter only Fiscal category
    df_fiscal_only = df_multi_year[df_multi_year["Category"] == "Fiscal"].copy()

    # 2. Aggregate by year
    df_fiscal_yearly = (
        df_fiscal_only.groupby("Year", as_index=False)["Impact"]
        .sum()
        .sort_values("Year")
    )

    # 3. Create static bar chart
    fig, ax = plt.subplots(figsize=(16, 6))

    bars = ax.bar(
        df_fiscal_yearly["Year"].astype(str),
        df_fiscal_yearly["Impact"],
        color="#f28e2b"  # colore fisso (puoi cambiarlo)
    )

    # 4. Add labels above each bar
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.2f}",
            ha="center",
            va="bottom",
            fontsize=10
        )

    ax.set_title("Cumulative Fiscal Impact on GDP Nowcast (2017–2025)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Cumulative Impact")

    st.pyplot(fig)

    # === AVERAGE ABSOLUTE IMPACT BY CATEGORY (STATIC MATPLOTLIB CHART) ===
    st.subheader("Average Absolute Impact by Category (With and Without 2020)")

    if all_year_impacts:
        df_multi_year = pd.concat(all_year_impacts, ignore_index=True)
        df_multi_year["Year"] = pd.Categorical(
            df_multi_year["Year"],
            categories=sorted(df_multi_year["Year"].unique()),
            ordered=True,
        )

        # Absolute impacts
        df_multi_year["AbsImpact"] = df_multi_year["Impact"].abs()

        # All years
        df_avg_all = (
            df_multi_year.groupby("Category", as_index=False)["AbsImpact"]
            .mean()
            .rename(columns={"AbsImpact": "Impact"})
            .assign(Type="All Years")
        )

        # Excluding 2020
        df_no2020 = df_multi_year[df_multi_year["Year"] != "2020"]
        df_avg_no2020 = (
            df_no2020.groupby("Category", as_index=False)["AbsImpact"]
            .mean()
            .rename(columns={"AbsImpact": "Impact"})
            .assign(Type="Excluding 2020")
        )

        # Combine
        df_avg_combined = pd.concat([df_avg_all, df_avg_no2020], ignore_index=True)

        # Static Plot with Matplotlib
        import matplotlib.pyplot as plt
        import numpy as np

        categories = df_avg_all["Category"].unique()
        x = np.arange(len(categories))

        impacts_all = df_avg_all["Impact"].values
        impacts_no2020 = df_avg_no2020["Impact"].values

        width = 0.25

        fig, ax = plt.subplots(figsize=(16, 6))
        ax.bar(x - width / 2, impacts_all, width, label="All Years", color="#4C9F70")
        ax.bar(x + width / 2, impacts_no2020, width, label="Excluding 2020", color="#C14B47")

        for i, v in enumerate(impacts_all):
            ax.text(x[i] - width / 2, v, f"{v:.2f}", ha="center", va="bottom")

        for i, v in enumerate(impacts_no2020):
            ax.text(x[i] + width / 2, v, f"{v:.2f}", ha="center", va="bottom")

        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha="right")
        ax.set_ylabel("Average Absolute Impact on GDP Nowcast")
        ax.set_title("Average Absolute GDP Impact by Category (All Years vs Excluding 2020)")
        ax.legend()

        st.pyplot(fig)

    else:
        st.warning("No impact data available for calculating averages.")

    # === Combined Accuracy and Bias Visualization ===
    st.subheader("Model Accuracy & Bias by Year")

    acc_bias_year = (
        metrics_all.groupby("year")[["RMSE", "MAE", "Bias"]]
        .mean()
        .sort_index()
    )

    acc_bias_all = acc_bias_year.mean().to_frame("Average (all years)").T
    acc_bias_excl = (
        metrics_all[metrics_all["year"] != "2020"]
        .groupby("year")[["RMSE", "MAE", "Bias"]]
        .mean()
        .mean()
        .to_frame("Average excl. 2020")
        .T
    )

    acc_bias_full = pd.concat([acc_bias_year, acc_bias_all, acc_bias_excl])
    acc_bias_full = acc_bias_full.reset_index().rename(columns={"index": "Year"})

    fig, ax = plt.subplots(figsize=(16, 6))
    width = 0.25
    x = range(len(acc_bias_full))

    ax.bar([p - width for p in x], acc_bias_full["RMSE"], width=width, label="RMSE", color="#0072B2")
    ax.bar(x, acc_bias_full["MAE"], width=width, label="MAE", color="#E69F00")
    ax.bar([p + width for p in x], acc_bias_full["Bias"], width=width, label="Bias", color="#009E73")

    ax.set_xticks(x)
    ax.set_xticklabels(acc_bias_full["Year"], rotation=45)
    ax.set_ylabel("Metric Value")
    ax.set_title("RMSE, MAE, and Bias by Year")
    ax.legend()
    for i, v in enumerate(acc_bias_full["RMSE"]):
        ax.text(i - width, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    for i, v in enumerate(acc_bias_full["MAE"]):
        ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    for i, v in enumerate(acc_bias_full["Bias"]):
        ax.text(i + width, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    st.pyplot(fig)

    # Forecast Volatility
    st.subheader("Forecast Volatility (Final Variance) by Year")
    vol_year = vols.groupby("year")["final_variance"].mean()
    vol_all = vol_year.mean()
    vol_excl = vols[vols["year"] != "2020"].groupby("year")["final_variance"].mean().mean()
    st.bar_chart(vol_year)
    st.write(f"Average volatility (all years): {vol_all:.3f}, Average excl. 2020: {vol_excl:.3f}")

    # Final absolute error by Year
    st.subheader("Final Absolute Error by Year (average across quarters)")
    fae_year = finals.groupby("year")["final_abs_error"].mean()
    fig, ax = plt.subplots(figsize=(16, 6))
    fae_year.plot(kind="bar", ax=ax, color="skyblue")
    ax.plot(
        range(len(fae_year)),
        fae_year.rolling(2, min_periods=1).mean(),
        color="red",
        linestyle="--",
        marker="o",
        label="Moving Avg Error",
    )
    ax.set_ylabel("Final Absolute Error")
    ax.legend()
    st.pyplot(fig)

    # === Releases vs Revisions Visualization ===
    import numpy as np

    st.subheader("Releases vs Revisions (Share) by Year")

    # Aggregate data
    rr_year = rr.groupby("year")[["releases", "revisions"]].sum()
    rr_year["releases_share"] = rr_year["releases"] / (rr_year["releases"] + rr_year["revisions"])
    rr_year["revisions_share"] = 1 - rr_year["releases_share"]

    # Averages
    rr_all = pd.DataFrame(
        {
            "releases_share": [rr_year["releases_share"].mean()],
            "revisions_share": [rr_year["revisions_share"].mean()],
        },
        index=["Average (all years)"],
    )

    rr_excl = pd.DataFrame(
        {
            "releases_share": [rr_year.drop("2020", errors="ignore")["releases_share"].mean()],
            "revisions_share": [rr_year.drop("2020", errors="ignore")["revisions_share"].mean()],
        },
        index=["Average excl. 2020"],
    )

    # Combine
    rr_full = pd.concat([rr_year, rr_all, rr_excl])
    rr_full = rr_full.reset_index().rename(columns={"index": "Year"})

    # Plot: two side-by-side bars
    fig, ax = plt.subplots(figsize=(16, 6))

    x = np.arange(len(rr_full))
    width = 0.25

    bars1 = ax.bar(x - width / 2, rr_full["releases_share"], width, label="Releases", color="#0072B2")
    bars2 = ax.bar(x + width / 2, rr_full["revisions_share"], width, label="Revisions", color="#D55E00")

    # Add numeric labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha='center', va='bottom'
        )

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha='center', va='bottom'
        )

    # Formatting
    ax.set_ylabel("Share of Total Impact")
    ax.set_xlabel("Year")
    ax.set_title("Releases vs Revisions Share by Year")
    ax.set_xticks(x)
    ax.set_xticklabels(rr_full["Year"], rotation=45)
    ax.legend()

    st.pyplot(fig)

    st.caption(
        """
    **Interpretation:**  
    Each bar shows the relative contribution of *new data releases* (in blue) and *statistical revisions* (in orange) to the changes in the GDP nowcast for that year.  
    A higher blue share indicates that nowcast updates were mainly driven by incoming information, while a larger orange share means that previously released data were revised substantially.  
    The last two bars summarize the average composition across all years, and excluding 2020.
    """
    )

    # === Average Absolute Error by Quarter (with and without 2020) ===
    st.subheader("Average Absolute Error by Quarter – Including vs Excluding 2020")

    abs_err_quarter_all = finals.groupby(finals["quarter"].str[-2:])["final_abs_error"].mean()
    abs_err_quarter_excl = finals[finals["year"] != "2020"].groupby(
        finals[finals["year"] != "2020"]["quarter"].str[-2:]
    )["final_abs_error"].mean()

    df_abs_err = pd.DataFrame(
        {
            "Quarter": abs_err_quarter_all.index,
            "All Years": abs_err_quarter_all.values,
            "Excl. 2020": abs_err_quarter_excl.values,
        }
    )

    fig, ax = plt.subplots(figsize=(16, 6))
    width = 0.25
    x = range(len(df_abs_err))

    ax.bar([p - width / 2 for p in x], df_abs_err["All Years"], width=width, label="All Years", color="#0072B2")
    ax.bar([p + width / 2 for p in x], df_abs_err["Excl. 2020"], width=width, label="Excl. 2020", color="#E69F00")

    ax.set_xticks(x)
    ax.set_xticklabels(df_abs_err["Quarter"], rotation=0)
    ax.set_ylabel("Average Absolute Error")
    ax.set_title("Average Absolute Error by Quarter")
    ax.legend()
    for i, v in enumerate(df_abs_err["All Years"]):
        ax.text(i - width / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    for i, v in enumerate(df_abs_err["Excl. 2020"]):
        ax.text(i + width / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)

    st.pyplot(fig)

    st.caption(
        """
    **Interpretation:**  
    Bars compare the average absolute forecast error per quarter when including all years (blue)  
    versus excluding 2020 (orange). Differences highlight how the pandemic year affected forecast accuracy.
    """
    )

    # Top 10 Variables Impact
    if all_impacts:
        df_impacts_all = pd.concat(all_impacts, ignore_index=True)

        # === Top 10 Variables ranked on ABSOLUTE impact (EXCLUDING 2020) ===

        # Remove 2020
        df_impacts_excl = df_impacts_all[df_impacts_all["year"] != "2020"]

        # Compute mean absolute impact per variable, EXCLUDING 2020
        top_vars_excl = (
            df_impacts_excl
            .assign(absImpact=df_impacts_excl["Impact"].abs())
            .groupby("Variable")["absImpact"]
            .mean()
            .sort_values(ascending=False)
            .head(10)
        )

        # Compute mean absolute impact ALSO for "all years", restricted to the selected top 10 variables
        top_vars_all = (
            df_impacts_all
            .assign(absImpact=df_impacts_all["Impact"].abs())
            .groupby("Variable")["absImpact"]
            .mean()
            .reindex(top_vars_excl.index)
        )

        # Build comparison dataframe
        df_compare = pd.DataFrame({
            "Variable": top_vars_excl.index,
            "Excl. 2020": top_vars_excl.values,
            "All Years": top_vars_all.values,
        }).melt(id_vars="Variable", var_name="Group", value_name="Impact")

        # Plot
        st.subheader("Top 10 Variables by Absolute Impact – Comparison")
        fig, ax = plt.subplots(figsize=(16, 6))
        sns.barplot(data=df_compare, x="Variable", y="Impact", hue="Group", ax=ax, width=0.4)
        ax.set_ylabel("Average Absolute Impact")
        ax.set_title("Top 10 Variables by Absolute Impact – Excluding 2020 vs All Years")
        ax.tick_params(axis="x", rotation=45)

        for container in ax.containers:
            ax.bar_label(container, fmt="%.2f", padding=3, fontsize=7)

        st.pyplot(fig)

    # ============================
    # TEST 1: Fiscal Variable Impact by Quarter (Matplotlib, non-interactive)
    # ============================
    st.subheader("Fiscal Variables: Average Absolute Impact by Quarter")

    fiscal_vars = ["GCEC1", "W875RX1", "MTSDS133FMS"]

    if all_impacts:
        df_all_imp = pd.concat(all_impacts, ignore_index=True)



        df_fiscal = df_all_imp[df_all_imp["Variable"].isin(fiscal_vars)].copy()
        df_fiscal["Quarter"] = df_fiscal["quarter"].str[-2:]  # q1, q2, q3, q4

        df_fiscal_avg = (
            df_fiscal.assign(AbsImpact=df_fiscal["Impact"].abs())
            .groupby(["Variable", "Quarter"], as_index=False)["AbsImpact"]
            .mean()
        )

        import matplotlib.pyplot as plt
        import numpy as np

        variables = df_fiscal_avg["Variable"].unique()
        quarters = ["q1", "q2", "q3", "q4"]
        x = np.arange(len(quarters))

        width = 0.25
        fig, ax = plt.subplots(figsize=(16, 6))

        for i, var in enumerate(variables):
            var_data = df_fiscal_avg[df_fiscal_avg["Variable"] == var].set_index("Quarter").reindex(quarters)
            bar = ax.bar(
                x + i * width - width,
                var_data["AbsImpact"],
                width,
                label=var
            )
            # numeric label above bars
            for rect in bar:
                height = rect.get_height()
                ax.annotate(f"{height:.3f}",
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(quarters)
        ax.set_ylabel("AbsImpact")
        ax.set_title("Average Absolute Fiscal Impact by Quarter")
        ax.legend()

        st.pyplot(fig)

    else:
        st.info("Fiscal impact data not available.")

    # ============================
    # TEST 2: Fiscal Variables Seasonality (Volatility per Quarter)
    # ============================
    st.subheader("Fiscal Variables: Seasonal Volatility by Quarter")

    if all_impacts:
        df_all_imp = pd.concat(all_impacts, ignore_index=True)

        df_fiscal = df_all_imp[df_all_imp["Variable"].isin(fiscal_vars)].copy()
        df_fiscal["Quarter"] = df_fiscal["quarter"].str[-2:]

        df_vol = (
            df_fiscal.groupby(["Variable", "Quarter"])["Impact"]
            .std()
            .reset_index(name="Volatility")
        )

        import matplotlib.pyplot as plt
        import numpy as np

        variables = df_vol["Variable"].unique()
        quarters = ["q1", "q2", "q3", "q4"]
        x = np.arange(len(quarters))

        width = 0.25
        fig, ax = plt.subplots(figsize=(16, 6))

        for i, var in enumerate(variables):
            var_data = df_vol[df_vol["Variable"] == var].set_index("Quarter").reindex(quarters)
            bar = ax.bar(
                x + i * width - width,
                var_data["Volatility"],
                width,
                label=var
            )
            # numeric label above bars
            for rect in bar:
                height = rect.get_height()
                ax.annotate(f"{height:.3f}",
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(quarters)
        ax.set_ylabel("Volatility")
        ax.set_title("Seasonal Volatility of Fiscal Variables (Impact Std by Quarter)")
        ax.legend()

        st.pyplot(fig)

    else:
        st.info("Fiscal volatility data not available.")


    # ============================================================
    # ===============  DIEBOLD–MARIANO TEST SECTION  =============
    # ============================================================

    import glob
    from scipy.stats import ttest_1samp

    st.header("Diebold–Mariano Tests: Fiscal Model vs Baseline")

    # ------------------------------------------------------------
    # 1. Errors database fiscal vs baseline
    # ------------------------------------------------------------

    BASE_NOW_NONFISC = NOWCAST_DIR.replace("_fiscal", "")  # cartella nowcast_Q

    files = glob.glob(os.path.join(BASE_NOW_NONFISC, "nowcast_*_q*.csv"))

    all_rows = []

    for file in files:
        base_name = os.path.basename(file)
        fiscal_file = os.path.join(NOWCAST_DIR, base_name.replace(".csv", "_fiscal.csv"))

        if not os.path.exists(fiscal_file):
            continue

        df_base = pd.read_csv(file)
        df_fisc = pd.read_csv(fiscal_file)

        name = base_name.replace("nowcast_", "").replace(".csv", "")
        year = int(name.split("_")[0])
        quarter = name.split("_")[1]

        df_tmp = pd.DataFrame({
            "year": year,
            "quarter": quarter,
            "error_base": df_base["error"],
            "error_fisc": df_fisc["error"]
        })

        all_rows.append(df_tmp)

    df_all = pd.concat(all_rows, ignore_index=True)

    # ------------------------------------------------------------
    # 2. Compute RMSE, MAE, Bias differential series
    # ------------------------------------------------------------

    df_all["d_rmse"] = df_all["error_base"] ** 2 - df_all["error_fisc"] ** 2
    df_all["d_mae"] = df_all["error_base"].abs() - df_all["error_fisc"].abs()
    df_all["d_bias"] = df_all["error_base"] - df_all["error_fisc"]


    def dm_test(series):
        stat, pval = ttest_1samp(series.dropna(), 0)
        return stat, pval


    # ------------------------------------------------------------
    # 3. Define periods
    # ------------------------------------------------------------

    periods = {
        "Full sample": df_all,
        "Excluding 2020": df_all[df_all["year"] != 2020],
        "Pre-2020": df_all[df_all["year"] < 2020],
        "Post-2020": df_all[df_all["year"] > 2020]
    }

    results = []

    for label, df in periods.items():
        stat_rmse, p_rmse = dm_test(df["d_rmse"])
        stat_mae, p_mae = dm_test(df["d_mae"])
        stat_bias, p_bias = dm_test(df["d_bias"])

        results.append({
            "Period": label,
            "DM_RMSE_stat": stat_rmse,
            "DM_RMSE_p": p_rmse,
            "DM_MAE_stat": stat_mae,
            "DM_MAE_p": p_mae,
            "DM_BIAS_stat": stat_bias,
            "DM_BIAS_p": p_bias
        })

    results_df = pd.DataFrame(results)
    st.subheader("Diebold–Mariano Test Results Table")
    st.dataframe(results_df, use_container_width=True)

    # ============================================================
    # ==========  DM STATISTICS  =============
    # ============================================================

    st.subheader("Diebold–Mariano Test – Combined Bar Chart (RMSE, MAE, Bias)")

    import numpy as np
    import matplotlib.pyplot as plt

    # Extract values
    periods = results_df["Period"].tolist()

    dm_rmse = results_df["DM_RMSE_stat"].values
    dm_mae = results_df["DM_MAE_stat"].values
    dm_bias = results_df["DM_BIAS_stat"].values

    x = np.arange(len(periods))
    width = 0.25

    fig, ax = plt.subplots(figsize=(16, 6))

    bars1 = ax.bar(x - width, dm_rmse, width, label="RMSE", color="#4C72B0")
    bars2 = ax.bar(x, dm_mae, width, label="MAE", color="#55A868")
    bars3 = ax.bar(x + width, dm_bias, width, label="Bias", color="#C44E52")

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.2f}",
                        xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    ax.axhline(0, color="black", linewidth=1)

    ax.set_xticks(x)
    ax.set_xticklabels(periods, rotation=25)
    ax.set_ylabel("DM Statistic")
    ax.set_title("Diebold–Mariano Test – RMSE vs MAE vs Bias (Fiscal – Baseline)")
    ax.legend()

    st.pyplot(fig)

#------------------------------------------------- NB
st.markdown("""
---
**NB:** The conditions applied in these nowcasts closely follow the New York Fed's methodology.  
DFM parameters are recalibrated at the beginning of each quarter.  
Each quarter is tracked starting roughly 22 weeks before the week of the advance GDP release, up until the week of the advance release.
""")
