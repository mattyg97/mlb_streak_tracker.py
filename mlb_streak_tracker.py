import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="MLB Player Streak Tracker", layout="wide")
st.title("⚾ MLB Active Player Streaks — Current 2025 Season")

SEASON = datetime.now().year  # Auto-detect current year
BASE_URL = "https://statsapi.mlb.com/api/v1"

@st.cache_data(ttl=86400)
def get_active_hitters():
    teams = requests.get(f"{BASE_URL}/teams?sportId=1").json()["teams"]
    players = []
    for t in teams:
        roster = requests.get(f"{BASE_URL}/teams/{t['id']}/roster?rosterType=active").json()["roster"]
        for p in roster:
            pos = p["position"]["abbreviation"]
            if pos in ["DH","1B","2B","3B","SS","LF","CF","RF","C"]:
                players.append({
                    "id": p["person"]["id"],
                    "name": p["person"]["fullName"],
                    "team": t["name"]
                })
    return players

def fetch_game_logs(player_id, limit=25):
    res = requests.get(f"{BASE_URL}/people/{player_id}/stats", params={"stats":"gameLog","season":SEASON}).json()
    splits = res.get("stats", [{}])[0].get("splits", [])
    return splits[:limit] if splits else []

def calculate_streak(logs, stat_key, cond):
    streak = 0
    for g in logs:
        val = g["stat"].get(stat_key, 0)
        if cond(val):
            streak += 1
        else:
            break
    return streak

@st.cache_data(ttl=3600)
def build_streak_data(min_total_bases=2):
    players = get_active_hitters()
    rows = []
    for p in players:
        logs = fetch_game_logs(p["id"])
        if not logs:
            continue

        hit_str = calculate_streak(logs, "hits", lambda x:x>0)
        rbi_str = calculate_streak(logs, "rbi", lambda x:x>0)
        run_str = calculate_streak(logs, "runs", lambda x:x>0)
        tb_str = calculate_streak(logs, "totalBases", lambda x: x>=min_total_bases)

        if max(hit_str, rbi_str, run_str, tb_str) == 0:
            continue

        rows.append({
            "Player": p["name"],
            "Team": p["team"],
            "Hitting": hit_str,
            "RBI": rbi_str,
            f"Total Bases ({min_total_bases}+)": tb_str,
            "Runs": run_str
        })
    return pd.DataFrame(rows)

# Sidebar controls
default_tb = st.number_input("Minimum total bases for TB streak", min_value=1, max_value=6, value=2)
min_len = st.slider("Minimum streak length to show", 1, 15, 2)
sort_choice = st.selectbox("Sort by streak type", ["Hitting","RBI",f"Total Bases ({default_tb}+)", "Runs"])
teams = build_streak_data(min_total_bases=default_tb)
filtered = teams[teams[sort_choice] >= min_len]
team_select = st.multiselect("Filter by team", options=sorted(filtered["Team"].unique()))
if team_select:
    filtered = filtered[filtered["Team"].isin(team_select)]

st.subheader("Current Active Streaks")
st.dataframe(filtered.sort_values(by=sort_choice, ascending=False).reset_index(drop=True), use_container_width=True)
