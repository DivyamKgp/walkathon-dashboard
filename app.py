# app.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px

# --- 0. Page & CSS setup ---
st.set_page_config(
    page_title="🏃 Walkathon 2.0 Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    [data-testid="stSidebar"] { background-color: #F3F2EF; }
</style>
""", unsafe_allow_html=True)

# --- 1. Scoring function ---
def calculate_score(steps):
    if steps < 8000:
        return steps
    if steps >= 15000:
        return 23000
    return 16000 + (steps - 8000)

# --- 2. Sidebar: upload & filters ---
with st.sidebar:
    st.header("🔄 Upload & Filter")
    uploaded = st.file_uploader(
        "CSV/Excel (cols: Date, Participant, Team, Steps)",
        type=["csv","xlsx"]
    )
    if not uploaded:
        st.info("Please upload your long-format Walkathon data.")
        st.stop()

    # load data
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded, parse_dates=["Date"])
    else:
        df = pd.read_excel(uploaded, parse_dates=["Date"], sheet_name="daily_wide", engine="openpyxl")
        # auto-melt if wide
        if "Participant" not in df.columns:
            participants = [c for c in df.columns if c != "Date"]
            df = df.melt(
                id_vars=["Date"],
                value_vars=participants,
                var_name="Participant",
                value_name="Steps"
            ).dropna(subset=["Steps"])
            team_map = {
                "Pranav": "Team 1", "Akshra": "Team 1", "Charishma": "Team 1", "Yash": "Team 1", "Vaishnavi": "Team 1",
                "Nisha": "Team 2", "Pavana": "Team 2", "Sakshi": "Team 2", "Muskan": "Team 2", "Ojasvi": "Team 2",
                "Ritesh": "Team 3", "Pravat": "Team 3", "Pragya": "Team 3", "Divyam": "Team 3", "Kasis": "Team 3",
                "Murali": "Team 4", "Surbhi": "Team 4", "Ankita": "Team 4", "Rohit": "Team 4", "Vanshita": "Team 4"
            }
            df["Team"] = df["Participant"].map(team_map)

    # compute score
    df["Score"] = df["Steps"].apply(calculate_score)

    # filters
    teams = df["Team"].unique().tolist()
    sel_teams = st.multiselect("Team", teams, default=teams)
    min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
    sel_dates = st.date_input("Date range", [min_date, max_date])

# --- 3. Filter data ---
mask = (
    df["Team"].isin(sel_teams)
    & df["Date"].dt.date.between(sel_dates[0], sel_dates[1])
)
df_filt = df[mask]

# --- 4. Tabs Layout ---
tab_overview, tab_team, tab_indv, tab_trends = st.tabs([
    "🏁 Overview", "🏆 Team Leaderboard",
    "🥇 Individual Board", "📈 Trends"
])

# === Overview: KPI Cards + Heatmap ===
with tab_overview:
    st.subheader("🚀 Key Metrics")
    total_steps     = int(df_filt["Steps"].sum())
    avg_daily_score = df_filt.groupby("Date")["Score"].sum().mean()
    pct_8k          = (df_filt["Steps"] >= 8000).mean() * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Steps", f"{total_steps:,}")
    c2.metric("Avg Daily Score", f"{avg_daily_score:,.0f}")
    c3.metric("% ≥ 8k Steps", f"{pct_8k:.1f}%")

    st.markdown("---")
    st.subheader("📅 Calendar Heatmap (Total Steps)")
    cal_data = df_filt.groupby("Date")["Steps"].sum().reset_index()
    cal_data["Weekday"] = cal_data["Date"].dt.weekday
    cal_data["Week"]    = cal_data["Date"].dt.isocalendar().week
    fig_cal = px.density_heatmap(
        cal_data,
        x="Weekday",
        y="Week",
        z="Steps",
        nbinsx=7,
        labels={"Weekday":"Day of Week", "Week":"Week #"},
        color_continuous_scale="Viridis",
        width=800,
        height=300
    )
    st.plotly_chart(fig_cal, use_container_width=True)

# === Team Leaderboard ===
with tab_team:
    st.subheader("🏆 Total Score by Team")
    team_totals = df_filt.groupby("Team")["Score"].sum().sort_values(ascending=False)
    st.bar_chart(team_totals)

    st.subheader("📊 Boxplot: Score Distribution by Team")
    fig, ax = plt.subplots()
    ax.boxplot(
        [df_filt[df_filt["Team"]==t]["Score"] for t in team_totals.index],
        labels=team_totals.index,
        vert=True
    )
    ax.set_ylabel("Score")
    st.pyplot(fig)

# === Individual Board ===
with tab_indv:
    st.subheader("🥇 Top Individuals")
    indv = (
        df_filt.groupby(["Participant","Team"])["Score"]
        .sum().reset_index()
        .sort_values("Score", ascending=False)
    )
    st.dataframe(indv.style.format({"Score":"{:,}"}), height=500)

# === Trends & Radar ===
with tab_trends:
    st.subheader("📈 Cumulative Score Over Time")
    cum = (
        df_filt.groupby(["Date","Team"])["Score"]
        .sum().reset_index()
        .pivot(index="Date", columns="Team", values="Score")
        .fillna(0).cumsum()
    )
    st.line_chart(cum)

    st.markdown("---")
    st.subheader("🎯 Radar Chart: Team Performance Metrics")
    radar_df = pd.DataFrame({
        "Metric": ["Total","Average","Max","Min"],
        **{
            team: [
                df_filt[df_filt["Team"]==team]["Score"].sum(),
                df_filt[df_filt["Team"]==team]["Score"].mean(),
                df_filt[df_filt["Team"]==team]["Score"].max(),
                df_filt[df_filt["Team"]==team]["Score"].min(),
            ]
            for team in team_totals.index
        }
    })
    # prepare data for radar
    radar_melt = radar_df.melt(id_vars="Metric", var_name="Team", value_name="Value")
    fig_radar = px.line_polar(
        radar_melt,
        r="Value",
        theta="Metric",
        color="Team",
        line_close=True,
        template="plotly_dark"
    )
    st.plotly_chart(fig_radar, use_container_width=True)
