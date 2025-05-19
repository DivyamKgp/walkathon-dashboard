import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# --- 0. Page config & CSS setup ---
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
    if steps < 8000: return steps
    if steps >= 15000: return 23000
    return 16000 + (steps - 8000)

# --- 2. Sidebar: demo + upload & filters ---
SAMPLE_DATA_PATH = "walkathon_daily_long.csv"

with st.sidebar:
    st.markdown("<h3 style='color:black;'>🔄 Upload & Filter</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:black;'>Upload your Walkathon data (CSV/Excel), or use our demo dataset below.</p>",
        unsafe_allow_html=True
    )

    use_demo = st.checkbox("🗃️ Use demo dataset", value=False)
    uploaded = None if use_demo else st.file_uploader(label="", type=["csv","xlsx"])

    if use_demo:
        df = pd.read_csv(SAMPLE_DATA_PATH, parse_dates=["Date"])
    elif uploaded:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded, parse_dates=["Date"])
        else:
            df = pd.read_excel(uploaded, parse_dates=["Date"], sheet_name="daily_wide", engine="openpyxl")
            if "Participant" not in df.columns:
                participants = [c for c in df.columns if c != "Date"]
                df = df.melt(
                    id_vars=["Date"],
                    value_vars=participants,
                    var_name="Participant",
                    value_name="Steps"
                ).dropna(subset=["Steps"])
                team_map = {
                    "Pranav":"Team 1","Akshra":"Team 1","Charishma":"Team 1","Yash":"Team 1","Vaishnavi":"Team 1",
                    "Nisha":"Team 2","Pavana":"Team 2","Sakshi":"Team 2","Muskan":"Team 2","Ojasvi":"Team 2",
                    "Ritesh":"Team 3","Pravat":"Team 3","Pragya":"Team 3","Divyam":"Team 3","Kasis":"Team 3",
                    "Murali":"Team 4","Surbhi":"Team 4","Ankita":"Team 4","Rohit":"Team 4","Vanshita":"Team 4"
                }
                df["Team"] = df["Participant"].map(team_map)
    else:
        st.info("Please upload a file or select the demo dataset.")
        st.stop()

    df["Score"] = df["Steps"].apply(calculate_score)
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
tab_overview, tab_team, tab_indv, tab_trends, tab_insights = st.tabs([
    "🏁 Overview", "🏆 Team Leaderboard",
    "🥇 Individual Board", "📈 Trends", "✨ Insights"
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

    st.subheader("📊 Score Distribution by Team")
    # Violin plot for richer distribution insights
    fig_violin = px.violin(
        df_filt, x="Team", y="Score", color="Team",
        box=True, points="all", hover_data=df_filt.columns
    )
    st.plotly_chart(fig_violin, use_container_width=True)

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
    # build radar DataFrame
    metrics = ["Total","Average","Max","Min"]
    radar_dict = {"Metric": metrics}
    for team in team_totals.index:
        scores = df_filt[df_filt["Team"] == team]["Score"]
        radar_dict[team] = [
            scores.sum(),
            scores.mean(),
            scores.max(),
            scores.min(),
        ]
    radar_df = pd.DataFrame(radar_dict)

    # Melt and plot
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

# === Insights: “Wow” Charts ===
with tab_insights:
    st.subheader("🏁 Animated Bar-Race of Teams")
    df_anim = (
        df_filt
        .groupby([df_filt["Date"].dt.strftime("%Y-%m-%d"), "Team"])["Score"]
        .sum()
        .reset_index()
        .rename(columns={"Date":"Day"})
    )
    fig_race = px.bar(
        df_anim,
        x="Score", y="Team", color="Team",
        orientation="h",
        animation_frame="Day",
        range_x=[0, df_anim["Score"].max() * 1.1],
        title="Team Score Race Over Time"
    )
    st.plotly_chart(fig_race, use_container_width=True)

    st.markdown("---")
    st.subheader("🌳 Sunburst: Score Contribution by Team & Member")
    sun_df = df_filt.groupby(["Team","Participant"])["Score"].sum().reset_index()
    fig_sun = px.sunburst(
        sun_df,
        path=["Team","Participant"],
        values="Score",
        color="Score",
        color_continuous_scale="Blues",
    )
    st.plotly_chart(fig_sun, use_container_width=True)

    st.markdown("---")
    st.subheader("⏱️ Gauge: Team Step Goals")
    # assume goal = 8000 * days * team_size
    days = df_filt["Date"].nunique()
    for team in team_totals.index:
        total_steps = df_filt[df_filt["Team"] == team]["Steps"].sum()
        goal = 8000 * days * (df_filt[df_filt["Team"] == team]["Participant"].nunique())
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=total_steps,
            delta={'reference': goal},
            gauge={'axis': {'range': [0, goal*1.2]}},
            title={'text': f"{team} Steps"}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown("---")
    st.subheader("📅 Individual Calendar Heatmap")
    sel_person = st.selectbox("Choose a participant", df["Participant"].unique())
    pcal = (
        df_filt[df_filt["Participant"] == sel_person]
        .groupby("Date")["Steps"]
        .sum().reset_index()
    )
    pcal["Weekday"] = pcal["Date"].dt.weekday
    pcal["Week"]    = pcal["Date"].dt.isocalendar().week
    fig_pcal = px.density_heatmap(
        pcal,
        x="Weekday",
        y="Week",
        z="Steps",
        nbinsx=7,
        color_continuous_scale="Magma",
        title=f"{sel_person}'s Step Heatmap"
    )
    st.plotly_chart(fig_pcal, use_container_width=True)
