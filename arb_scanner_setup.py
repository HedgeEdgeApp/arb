# Arbitrage Betting Scanner (Streamlit UI)

import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# === Configuration ===
API_KEY = st.secrets["API_KEY"]  # Stored securely in Streamlit Cloud
REGION = 'eu'
MARKET = 'h2h'
ODDS_FORMAT = 'decimal'
NZ_TZ = pytz.timezone("Pacific/Auckland")

# === Helper Functions ===
def fetch_all_sports():
    url = 'https://api.the-odds-api.com/v4/sports/'
    params = {'apiKey': API_KEY}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error(f"API Error fetching sports: {response.status_code} - {response.text}")
        return []
    return response.json()

def fetch_odds_for_sport(sport_key):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/'
    params = {
        'regions': REGION,
        'markets': MARKET,
        'oddsFormat': ODDS_FORMAT,
        'apiKey': API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return []
    return response.json()

def find_arbs(odds_data, sport_name):
    arbs = []
    for event in odds_data:
        try:
            if 'bookmakers' not in event or not event['bookmakers']:
                continue

            outcomes = {}
            team_names = event.get('teams')
            if not team_names:
                home = event.get('home_team', '')
                away = event.get('away_team', '')
                team_names = f"{home} vs {away}" if home or away else "Unknown Match"
            else:
                team_names = ' vs '.join(team_names)

            if event.get('commence_time') is None:
                event_time_display = "LIVE"
                countdown = "Ongoing"
            else:
                event_utc = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
                event_nz = event_utc.astimezone(NZ_TZ)
                now_nz = datetime.now(NZ_TZ)
                event_time_display = event_nz.strftime("%Y-%m-%d %H:%M NZT")
                delta = event_nz - now_nz
                countdown = str(delta).split('.')[0] if delta.total_seconds() > 0 else "Ongoing"

            for bookmaker in event['bookmakers']:
                for market in bookmaker.get('markets', []):
                    if market.get('key') != 'h2h':
                        continue
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name')
                        price = outcome.get('price')
                        if not name or not price:
                            continue
                        if name not in outcomes or price > outcomes[name]['price']:
                            outcomes[name] = {
                                'price': price,
                                'bookmaker': bookmaker.get('title', 'Unknown')
                            }

            if len(outcomes) != 2:
                continue

            inv_sum = sum(1 / outcome['price'] for outcome in outcomes.values())
            if inv_sum < 1:
                arb_margin = (1 - inv_sum) * 100
                arbs.append({
                    'Sport': sport_name,
                    'Match': team_names,
                    'Start Time': event_time_display,
                    'Countdown': countdown,
                    'Team 1': list(outcomes.keys())[0],
                    'Odds 1': list(outcomes.values())[0]['price'],
                    'Bookie 1': list(outcomes.values())[0]['bookmaker'],
                    'Team 2': list(outcomes.keys())[1],
                    'Odds 2': list(outcomes.values())[1]['price'],
                    'Bookie 2': list(outcomes.values())[1]['bookmaker'],
                    'Arb Margin (%)': round(arb_margin, 2),
                    'Highlight': event_time_display == "LIVE"
                })
        except Exception as e:
            st.warning(f"Skipped a match due to error: {e}")
            continue
    return arbs

# === Streamlit UI ===
st.set_page_config(page_title="Arbitrage Scanner", layout="wide")
st.title("📈 Arbitrage Betting Scanner")

col1, col2 = st.columns([3, 1])
with col1:
    min_margin = st.slider("Minimum Arbitrage Margin (%)", 0.0, 10.0, 0.5, 0.1)
with col2:
    show_raw = st.checkbox("Show raw odds data")

if st.button("🔍 Scan ALL Sports for Arbitrage Opportunities"):
    with st.spinner("Fetching all sports and odds data..."):
        sports = fetch_all_sports()
        all_arbs = []
        raw_odds_summary = []

        for sport in sports:
            odds_data = fetch_odds_for_sport(sport['key'])
            raw_odds_summary.extend(odds_data)
            arbs = find_arbs(odds_data, sport.get('title', sport['key']))
            filtered = [a for a in arbs if a['Arb Margin (%)'] >= min_margin]
            all_arbs.extend(filtered)

        if show_raw:
            st.subheader("📦 Raw Odds Data")
            st.json(raw_odds_summary)

        if not all_arbs:
            st.info("No arbitrage opportunities found across all sports.")
        else:
            df = pd.DataFrame(all_arbs).sort_values(by='Start Time')
            st.success(f"Found {len(all_arbs)} arbitrage opportunities across all sports!")

            def highlight_live(row):
                return ['background-color: #ffd6d6' if row['Highlight'] else '' for _ in row]

            st.dataframe(
                df.drop(columns=['Highlight']).style.apply(highlight_live, axis=1),
                use_container_width=True
            )
