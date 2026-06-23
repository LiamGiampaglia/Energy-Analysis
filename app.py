import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from docx import Document
from docx.shared import Inches
import io

st.set_page_config(layout="wide")
st.title("⚡ Energy Analysis Dashboard")

# -----------------------------
# Upload files
# -----------------------------
files = st.file_uploader(
    "Upload energy data (single or multiple files)",
    type=["xlsx", "csv"],
    accept_multiple_files=True
)

# -----------------------------
# MAIN APP
# -----------------------------
if files:

    all_data = []

    # -----------------------------
    # LOAD + CLEAN DATA
    # -----------------------------
    for file in files:

        if file.name.endswith(".csv"):
            temp_df = pd.read_csv(file)
        else:
            temp_df = pd.read_excel(file, engine="openpyxl", skiprows=1)

        temp_df.columns = temp_df.columns.str.strip()

        # ✅ Detect format
        if temp_df.shape[1] > 2:

            # Wide format → melt
            date_col = temp_df.columns[0]

            temp_df = temp_df.rename(columns={date_col: "date"})

            temp_df = temp_df.melt(
                id_vars=["date"],
                var_name="interval",
                value_name="consumption"
            )

            temp_df["date"] = pd.to_datetime(temp_df["date"], dayfirst=True, errors="coerce")

            temp_df["interval"] = temp_df.groupby("date").cumcount()

            temp_df["datetime"] = temp_df["date"] + pd.to_timedelta(
                temp_df["interval"] * 30, unit="minutes"
            )

            temp_df = temp_df.drop(columns=["date", "interval"])

        else:
            # Standard format
            temp_df = temp_df.rename(columns={
                "Date": "datetime",
                "Value": "consumption"
            })

            temp_df["datetime"] = pd.to_datetime(
                temp_df["datetime"], dayfirst=True, errors="coerce"
            )

        # Clean
        temp_df = temp_df.dropna(subset=["datetime", "consumption"])

        # ✅ Add fuel type
        if "gas" in file.name.lower():
            temp_df["fuel"] = "Gas"
        elif "elec" in file.name.lower() or "electric" in file.name.lower():
            temp_df["fuel"] = "Electricity"
        else:
            temp_df["fuel"] = "Unknown"

        all_data.append(temp_df)

    df = pd.concat(all_data)
    df = df.sort_values("datetime")

    # -----------------------------
    # SIDEBAR FILTERS
    # -----------------------------
    st.sidebar.header("Filters")

    fuel_options = df["fuel"].unique()
    selected_fuel = st.sidebar.selectbox("Fuel Type", ["All"] + list(fuel_options))

    if selected_fuel != "All":
        df = df[df["fuel"] == selected_fuel]

    meter_column = st.sidebar.selectbox("Meter Column", ["None"] + list(df.columns))

    if meter_column != "None":
        meters = df[meter_column].dropna().unique()
        selected_meter = st.sidebar.selectbox("Select Meter", ["All"] + list(meters))

        if selected_meter != "All":
            df = df[df[meter_column] == selected_meter]
        else:
            df = df.groupby("datetime")["consumption"].sum().reset_index()

    # -----------------------------
    # FEATURE ENGINEERING
    # -----------------------------
    df = df.sort_values("datetime")

    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour + df["datetime"].dt.minute / 60
    df["day"] = df["datetime"].dt.day_name()
    df["weekday"] = df["datetime"].dt.dayofweek
    df["is_weekend"] = df["weekday"] >= 5

    # -----------------------------
    # METRICS
    # -----------------------------
    base_load = df["consumption"].quantile(0.1)
    avg_load = df["consumption"].mean()
    peak_load = df["consumption"].max()

    day_load = df[(df["hour"] >= 8) & (df["hour"] <= 18)]["consumption"].mean()
    night_load = df[(df["hour"] < 6)]["consumption"].mean()

    weekday_avg = df[~df["is_weekend"]]["consumption"].mean()
    weekend_avg = df[df["is_weekend"]]["consumption"].mean()

    load_std = df["consumption"].std()

    report_items = []

    # -----------------------------
    # TIME SERIES
    # -----------------------------
    st.subheader("📈 Time Series")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["datetime"], df["consumption"])
    st.pyplot(fig)

    report_items.append(("Time Series", "Energy trend over time", io.BytesIO()))

    # -----------------------------
    # DAILY PROFILE
    # -----------------------------
    st.subheader("📊 Daily Profile")
    profile = df.groupby("hour")["consumption"].mean()

    fig, ax = plt.subplots()
    ax.plot(profile)
    st.pyplot(fig)

    # -----------------------------
    # HEATMAP (ONLY IF INTRADAY)
    # -----------------------------
    if df["hour"].nunique() > 1:

        st.subheader("🔥 Heatmap")

        heatmap = df.pivot_table(
            index="date",
            columns="hour",
            values="consumption"
        )

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(heatmap, cmap="coolwarm", ax=ax)
        st.pyplot(fig)

    # -----------------------------
    # LOAD DURATION
    # -----------------------------
    st.subheader("⚡ Load Duration Curve")
    ldc = df["consumption"].sort_values(ascending=False)

    fig, ax = plt.subplots()
    ax.plot(ldc.values)
    st.pyplot(fig)

    # -----------------------------
    # RECOMMENDATIONS
    # -----------------------------
    recommendations = []

    if night_load > base_load * 1.2:
        recommendations.append("Reduce out-of-hours consumption")

    if weekend_avg > weekday_avg * 0.8:
        recommendations.append("Investigate weekend usage")

    if peak_load > avg_load * 1.5:
        recommendations.append("Reduce peak demand")

    st.subheader("💡 Recommendations")

    for r in recommendations:
        st.write("-", r)

    # -----------------------------
    # COPILOT PROMPT
    # -----------------------------
    copilot_prompt = f"""
Analyse this energy data:

Base load {base_load:.1f}
Average {avg_load:.1f}
Peak {peak_load:.1f}

Provide:
- Key insights
- Inefficiencies
- Recommendations
"""

    st.subheader("🤖 Copilot Prompt")
    st.code(copilot_prompt)

    # -----------------------------
    # WORD REPORT
    # -----------------------------
    def create_word_report():
        doc = Document()
        doc.add_heading("Energy Report", 0)

        doc.add_heading("Key Metrics", 1)
        doc.add_paragraph(f"Base load: {base_load:.1f}")
        doc.add_paragraph(f"Peak load: {peak_load:.1f}")

        doc.add_heading("Recommendations", 1)
        for r in recommendations:
            doc.add_paragraph(f"- {r}")

        doc.add_heading("Copilot Prompt", 1)
        doc.add_paragraph(copilot_prompt)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream

    st.download_button(
        "📄 Download Report",
        create_word_report(),
        file_name="energy_report.docx"
    )
