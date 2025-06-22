# Arbitrage Betting Scanner (Streamlit UI)

import requests
import streamlit as st
import pandas as pd

# === Configuration ===
API_KEY = st.secrets["API_KEY"]  # Stored securely in Streamlit Cloud
DEFAULT_SPORT = 'tennis'
REGION = 'eu'
MARKET = 'h2h'
ODDS_FORMAT = 'decimal'

# === Helper Functions ===
def fetch_odds(sport):
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/'
    params = {
        'regions': REGION,
        'markets': MARKET,
        'oddsFormat': ODDS_FORMAT,
        'apiKey': API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error(f"API Error: {response.status_code} - {response.text}")
        return []
    return response.json()

def find_arbs(odds_data):
    arbs = []
    for event in odds_data:
        outcomes = {}
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
                    'Match': ' vs '.join(event['teams']),
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
st.title("📈 Arbitrage Betting Scanner")

sport = st.selectbox("Select a sport:", [
    'tennis', 'basketball_nba', 'soccer_epl', 'mma_mixed_martial_arts', 'baseball_mlb', 'americanfootball_nfl'
], index=0)

min_margin = st.slider("Minimum Arbitrage Margin (%)", 0.0, 10.0, 0.5, 0.1)

if st.button("🔍 Scan for Arbitrage Opportunities"):
    with st.spinner("Fetching odds and checking for arbitrage..."):
        data = fetch_odds(sport)
        arbs = find_arbs(data)
        filtered = [a for a in arbs if a['Arb Margin (%)'] >= min_margin]

        if not filtered:
            st.info("No arbitrage opportunities found.")
        else:
            df = pd.DataFrame(filtered)
            st.success(f"Found {len(filtered)} arbitrage opportunities!")
            st.dataframe(df, use_container_width=True)
