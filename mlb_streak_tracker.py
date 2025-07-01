import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="MLB Player Streak Tracker", layout="wide")
st.title("⚾ MLB Active Player Streaks (2025)")

SEASON = 2025
BASE_URL = "https://statsapi.mlb.com/api/v1"

@st.cache_data(ttl=86400)
def get_active_hitters():
    url = f"{BASE_URL}/teams?sportId=1"
    teams = requests.get(url).json()["teams"]
    all_players = []
    for team in teams:
        team_id = team["id"]
        roster_url = f"{BASE_URL}/teams/{team_id}/roster?rosterType=active"
        r = requests.get(roster_url).json()
        for player in r["roster"]:
            pos = player["position"]["abbreviation"]
            if pos in ["DH", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "C"]:
                all_players.append({
                    "id": player["person"]["id"],
                    "name": player["person"]["fullName"],
                    "team": team["name"]
                })
    return all_players

def fetch_game_logs(player_id, limit=20):
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
    params = {
        "stats": "gameLog",
        "season": SEASON
    }
    r = requests.get(url, params=params).json()
    try:
        return r["stats"][0]["splits"][:limit]
    except:
        return []

def calculate_streak(logs, stat_key, condition_fn):
    streak = 0
    for g in logs:
        val = g["stat"].get(stat_key, 0)
        if condition_fn(val):
            streak += 1
        else:
            break
    return streak

@st.cache_data(ttl=3600)
def build_streak_data():
    players = get_active_hitters()
    streaks = []
    for p in players:
        logs = fetch_game_logs(p["id"])
        if not logs:
            continue

        hit_streak = calculate_streak(logs, "hits", lambda h: h > 0)
        rbi_streak = calculate_streak(logs, "rbi", lambda r: r > 0)
        run_streak = calculate_streak(logs, "runs", lambda r: r > 0)
        tb_streak = calculate_streak(logs, "totalBases", lambda tb: tb >= 2)

        if max(hit_streak, rbi_streak, run_streak, tb_streak) == 0:
            continue  # Skip players with no streaks

        streaks.append({
            "Player": p["name"],
            "Team": p["team"],
            "Hitting": hit_streak,
            "RBI": rbi_streak,
            "Total Bases (2+)": tb_streak,
            "Runs": run_streak
        })

    return pd.DataFrame(streaks)

df = build_streak_data()

# ---------------- UI ----------------
min_length = st.slider("Minimum streak length to show", 1, 15, 2)
sort_by = st.selectbox("Sort by", ["Hitting", "RBI", "Total Bases (2+)", "Runs"])
team_filter = st.multiselect("Filter by team", options=sorted(df["Team"].unique()))

df_filtered = df[df[sort_by] >= min_length]
if team_filter:
    df_filtered = df_filtered[df_filtered["Team"].isin(team_filter)]

df_sorted = df_filtered.sort_values(by=sort_by, ascending=False)
st.subheader(f"Active Player Streaks (Sorted by {sort_by})")
st.dataframe(df_sorted.reset_index(drop=True), use_container_width=True)
