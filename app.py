import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from docx import Document
from docx.shared import Inches
import io


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
        df = pd.read_excel(file, engine="openpyxl", skiprows=1)

    # -----------------------------
    # Standardise columns
    # -----------------------------
    df.columns = df.columns.str.strip()

    # Rename for consistency
    
    df = df.rename(columns={
        "Date": "datetime",
        "Value": "consumption"
    })
    
    # Convert datetime
    
    df["datetime"] = pd.to_datetime(df["datetime"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["datetime"])

    # Sort
    df = df.sort_values("datetime")

    # Feature engineering
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour + df["datetime"].dt.minute / 60
    df["day"] = df["datetime"].dt.day_name()
    df["weekday"] = df["datetime"].dt.dayofweek
    df["is_weekend"] = df["weekday"] >= 5

    # -----------------------------
    # Key metrics
    # -----------------------------
    base_load = df["consumption"].quantile(0.1)
    avg_load = df["consumption"].mean()
    peak_load = df["consumption"].max()
    
    # Day vs night
    day_load = df[(df["hour"] >= 8) & (df["hour"] <= 18)]["consumption"].mean()
    night_load = df[(df["hour"] < 6)]["consumption"].mean()
    
    # Weekend comparison
    weekday_avg = df[df["is_weekend"] == False]["consumption"].mean()
    weekend_avg = df[df["is_weekend"] == True]["consumption"].mean()
    
    # Variability
    load_std = df["consumption"].std()
    
    report_items = []

    # -----------------------------
    # 1. Time Series
    # -----------------------------
    st.subheader("📈 Time Series")

    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(df["datetime"], df["consumption"])
    ax.set_ylabel("kWh")
    st.pyplot(fig)

    st.markdown(f"""
        **Insight:**  
        The time series shows energy consumption ranging from approximately **{base_load:.1f} kWh to {peak_load:.1f} kWh**.  
        Average demand is **{avg_load:.1f} kWh**, indicating overall site usage.
        
        Daily cycling is clearly visible, suggesting structured operational hours.  
        {'Significant variation between peaks and troughs indicates strong operational influence on demand.' if peak_load > base_load * 2 else 'Relatively stable demand suggests more constant operational usage.'}
        """)

    
    st.markdown(text)
    
    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Time Series", text, img))


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

    st.markdown(f"""
    **Insight:**  
    The average daily profile shows a **base load of ~{base_load:.1f} kWh** during low-use periods 
    and peak demand reaching **~{peak_load:.1f} kWh** during active hours.
    
    Daytime consumption averages **{day_load:.1f} kWh**, compared to night-time levels of **{night_load:.1f} kWh**.
    
    {'A strong increase during working hours indicates occupancy-driven demand.' if day_load > night_load * 1.5 else 'Limited variation suggests equipment may be running continuously.'}
    """)

    st.markdown(text)
    
    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Average Daily Load Profile", text, img))

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

    st.markdown(f"""
    **Insight:**  
    Average weekday consumption is **{weekday_avg:.1f} kWh**, compared to **{weekend_avg:.1f} kWh** on weekends.
    
    {'There is a clear reduction in weekend consumption, indicating reduced occupancy and operational activity.' if weekend_avg < weekday_avg * 0.8 else 'Weekend consumption remains relatively high, suggesting systems may be running unnecessarily outside working hours.'}
    """)

    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Weekday vs Weekend", text, img))

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

    st.markdown(f"""
    **Insight:**  
    The heatmap highlights consistent daily patterns, with higher consumption concentrated during peak hours.
    
    Load variability (standard deviation = **{load_std:.1f} kWh**) indicates 
    {'significant fluctuations in demand across the dataset.' if load_std > 10 else 'relatively stable consumption patterns.'}
    
    This visual is particularly useful for identifying anomalies or unusual spikes in demand.
    """)

    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Heatmap", text, img))

    # -----------------------------
    # 5. Load Duration Curve
    # -----------------------------
    st.subheader("⚡ Load Duration Curve")

    ldc = df["consumption"].sort_values(ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots()
    ax.plot(ldc)
    ax.set_ylabel("kWh")
    st.pyplot(fig)

    st.markdown(f"""
    **Insight:**  
    The load duration curve shows that peak demand reaches **{peak_load:.1f} kWh**, 
    while the base load remains around **{base_load:.1f} kWh**.
    
    {'The steep curve suggests short periods of high demand.' if peak_load > avg_load * 1.5 else 'The relatively flat curve suggests consistent energy use across the period.'}
    
    This indicates how frequently high loads occur and helps separate base load from operational demand.
    """)


    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Load Duration Curve", text, img))
    
    # -----------------------------
    # 6. Peak Demand
    # -----------------------------
    st.subheader("🔺 Daily Peak Demand")

    peak = df.groupby("date")["consumption"].max()

    fig, ax = plt.subplots()
    ax.plot(peak.index, peak.values)
    ax.set_ylabel("Peak kWh")
    st.pyplot(fig)

    st.markdown(f"""
    **Insight:**  
    Daily peak demand reaches up to **{peak_load:.1f} kWh**, indicating the highest operational load on site.
    
    Monitoring peak demand is important for identifying unusually high consumption days and potential cost impacts.
    
    {'High peaks relative to average demand suggest opportunities to reduce maximum load.' if peak_load > avg_load * 1.5 else 'Peak demand is relatively stable compared to average usage.'}
    """)

    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Peak Demand", text, img))

    # -----------------------------
    # 7. Histogram
    # -----------------------------
    st.subheader("📉 Load Distribution")

    fig, ax = plt.subplots()
    ax.hist(df["consumption"], bins=40)
    ax.set_xlabel("kWh")
    st.pyplot(fig)

    st.markdown(f"""
    **Insight:**  
    The distribution shows most consumption values centred around **{avg_load:.1f} kWh**, 
    with a base load near **{base_load:.1f} kWh**.
    
    {'A wide spread of values indicates varied operational demand throughout the day.' if load_std > 10 else 'A narrow distribution suggests consistent energy usage.'}
    """)

    # Save figure
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    
    report_items.append(("Histogram", text, img))

    # -----------------------------
    # Download charts-ready data
    # -----------------------------
    
    st.subheader("📄 Download Energy Report")
    
    def create_word_report():
        doc = Document()
        doc.add_heading("Energy Analysis Report", 0)
    
        for title, text, img in report_items:
            doc.add_heading(title, level=1)
            doc.add_paragraph(text)
    
            # Add image
            doc.add_picture(img, width=Inches(6))
    
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
    
        return file_stream
    
    
    word_file = create_word_report()
    
    st.download_button(
        label="Download Word Report",
        data=word_file,
        file_name="energy_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
