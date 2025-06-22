# Arbitrage Betting Scanner (Streamlit UI)

import requests
import streamlit as st
import pandas as pd

# === Configuration ===
API_KEY = st.secrets["API_KEY"]  # Stored securely in Streamlit Cloud
REGION = 'eu'  # Accessing all available free bookmakers in EU region
MARKET = 'h2h'
ODDS_FORMAT = 'decimal'

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

def find_arbs(odds_data):
    arbs = []
    for event in odds_data:
        outcomes = {}
        team_names = event.get('teams') or event.get('home_team', '') + ' vs ' + event.get('away_team', '')
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] != 'h2h':
                    continue
                for outcome in market['outcomes']:
                    name = outcome['name']
                    if name not in outcomes or outcome['price'] > outcomes[name]['price']:
                        outcomes[name] = {
                            'price': outcome['price'],
                            'bookmaker': bookmaker['title']
                        }
        if len(outcomes) == 2:
            inv_sum = sum(1 / outcome['price'] for outcome in outcomes.values())
            if inv_sum < 1:
                arb_margin = (1 - inv_sum) * 100
                arbs.append({
                    'Match': team_names,
                    'Team 1': list(outcomes.keys())[0],
                    'Odds 1': list(outcomes.values())[0]['price'],
                    'Bookie 1': list(outcomes.values())[0]['bookmaker'],
                    'Team 2': list(outcomes.keys())[1],
                    'Odds 2': list(outcomes.values())[1]['price'],
                    'Bookie 2': list(outcomes.values())[1]['bookmaker'],
                    'Arb Margin (%)': round(arb_margin, 2)
                })
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
            arbs = find_arbs(odds_data)
            filtered = [a for a in arbs if a['Arb Margin (%)'] >= min_margin]
            all_arbs.extend(filtered)

        if show_raw:
            st.subheader("📦 Raw Odds Data")
            st.json(raw_odds_summary)

        if not all_arbs:
            st.info("No arbitrage opportunities found across all sports.")
        else:
            df = pd.DataFrame(all_arbs)
            st.success(f"Found {len(all_arbs)} arbitrage opportunities across all sports!")
            st.dataframe(df, use_container_width=True)
