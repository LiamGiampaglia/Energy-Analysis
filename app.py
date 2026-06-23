import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(layout="wide")
st.title("⚡ Energy Analysis Dashboard (Half-Hourly Data)")

# -----------------------------
# Upload file
# -----------------------------
file = st.file_uploader("Upload Schneider Electric data", type=["xlsx", "csv"])

if file:
    # Read file
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")

    # -----------------------------
    # Standardise columns
    # -----------------------------
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df = df.rename(columns={
        df.columns[0]: "datetime",
        df.columns[1]: "consumption"
    })

    # Convert datetime
    df["datetime"] = pd.to_datetime(df["datetime"], dayfirst=True)

    # Sort
    df = df.sort_values("datetime")

    # Feature engineering
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour + df["datetime"].dt.minute / 60
    df["day"] = df["datetime"].dt.day_name()
    df["weekday"] = df["datetime"].dt.dayofweek
    df["is_weekend"] = df["weekday"] >= 5

    st.subheader("✅ Cleaned Data")
    st.write(df.head())

    # -----------------------------
    # 1. Time Series
    # -----------------------------
    st.subheader("📈 Time Series")

    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(df["datetime"], df["consumption"])
    ax.set_ylabel("kWh")
    st.pyplot(fig)

    # -----------------------------
    # 2. Average Daily Profile
    # -----------------------------
    st.subheader("📊 Average Daily Load Profile")

    avg_profile = df.groupby("hour")["consumption"].mean()

    fig, ax = plt.subplots()
    ax.plot(avg_profile.index, avg_profile.values)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Average kWh")
    st.pyplot(fig)

    # -----------------------------
    # 3. Weekday vs Weekend
    # -----------------------------
    st.subheader("📅 Weekday vs Weekend")

    weekday = df[df["is_weekend"] == False].groupby("hour")["consumption"].mean()
    weekend = df[df["is_weekend"] == True].groupby("hour")["consumption"].mean()

    fig, ax = plt.subplots()
    ax.plot(weekday.index, weekday.values, label="Weekday")
    ax.plot(weekend.index, weekend.values, label="Weekend")
    ax.legend()
    st.pyplot(fig)

    # -----------------------------
    # 4. Heatmap
    # -----------------------------
    st.subheader("🔥 Heatmap")

    heatmap = df.pivot_table(
        index="date",
        columns="hour",
        values="consumption",
        aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(12,6))
    sns.heatmap(heatmap, cmap="coolwarm", ax=ax)
    st.pyplot(fig)

    # -----------------------------
    # 5. Load Duration Curve
    # -----------------------------
    st.subheader("⚡ Load Duration Curve")

    ldc = df["consumption"].sort_values(ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots()
    ax.plot(ldc)
    ax.set_ylabel("kWh")
    st.pyplot(fig)

    # -----------------------------
    # 6. Peak Demand
    # -----------------------------
    st.subheader("🔺 Daily Peak Demand")

    peak = df.groupby("date")["consumption"].max()

    fig, ax = plt.subplots()
    ax.plot(peak.index, peak.values)
    ax.set_ylabel("Peak kWh")
    st.pyplot(fig)

    # -----------------------------
    # 7. Histogram
    # -----------------------------
    st.subheader("📉 Load Distribution")

    fig, ax = plt.subplots()
    ax.hist(df["consumption"], bins=40)
    ax.set_xlabel("kWh")
    st.pyplot(fig)

    # -----------------------------
    # Download charts-ready data
    # -----------------------------
    st.subheader("📥 Download prepared data")

    st.download_button(
        "Download cleaned CSV",
        df.to_csv(index=False),
        file_name="cleaned_energy_data.csv"
    )
