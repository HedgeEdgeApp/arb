# 🔍 Arbitrage Betting Scanner (Web-Scraping Version - Free & Legal)

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re

# === Config ===
NZ_TZ = pytz.timezone("Pacific/Auckland")
HEADERS = {"User-Agent": "Mozilla/5.0"}
ODDSPORTAL_URL = "https://www.oddsportal.com/matches/"

# === Streamlit Setup ===
st.set_page_config(page_title="Free Arbitrage Scanner", layout="wide")
st.title("📈 Free Arbitrage Betting Scanner (OddsPortal Live)")

col1, col2 = st.columns([3, 1])
with col1:
    min_margin = st.slider("Minimum Arbitrage Margin (%)", 0.0, 10.0, 0.5, 0.1)
with col2:
    refresh = st.checkbox("🔄 Refresh Odds", value=True)

@st.cache_data(ttl=600)
def scrape_oddsportal():
    url = ODDSPORTAL_URL
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find match rows
        match_rows = soup.find_all("div", class_=re.compile("^match-row"))
        events = []
        for row in match_rows:
            try:
                teams = row.find("div", class_="match-name").text.strip()
                time_raw = row.find("div", class_="match-time").text.strip()
                bookie_odds = row.find_all("div", class_="odds")

                if not teams or not bookie_odds:
                    continue

                odds = [float(od.text.strip()) for od in bookie_odds if re.match(r"^[0-9]+\.[0-9]+$", od.text.strip())]
                if len(odds) < 2:
                    continue

                # Convert to NZ time estimate (not always shown precisely)
                now_nz = datetime.now(NZ_TZ)
                if ":" in time_raw:
                    hour, minute = map(int, time_raw.split(":"))
                    start_dt = now_nz.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if start_dt < now_nz:
                        start_dt += timedelta(days=1)
                else:
                    start_dt = now_nz  # Assume live

                inv_sum = sum(1/o for o in odds[:2])
                arb_margin = (1 - inv_sum) * 100 if inv_sum < 1 else 0

                events.append({
                    "Match": teams,
                    "Odds 1": odds[0],
                    "Odds 2": odds[1],
                    "Arb Margin (%)": round(arb_margin, 2),
                    "Start Time (NZT)": start_dt.strftime("%Y-%m-%d %H:%M"),
                    "Countdown": "LIVE" if start_dt <= now_nz else str(start_dt - now_nz).split(".")[0],
                    "Live": start_dt <= now_nz
                })
            except:
                continue

        return events
    except Exception as e:
        st.error(f"Failed to scrape odds: {e}")
        return []

# === Main Logic ===
if refresh:
    with st.spinner("Scraping live odds from OddsPortal..."):
        data = scrape_oddsportal()
        if not data:
            st.warning("No events found. OddsPortal may be offline or layout changed.")
        else:
            df = pd.DataFrame(data)
            df = df[df["Arb Margin (%)"] >= min_margin]
            df = df.sort_values(by=["Live", "Start Time (NZT)"], ascending=[False, True])

            if df.empty:
                st.info("No arbitrage opportunities found above the selected margin.")
            else:
                def highlight_live(row):
                    return ["background-color: #ffdddd" if row.Live else "" for _ in row]

                st.success(f"Found {len(df)} events with potential arbitrage!")
                st.dataframe(df.style.apply(highlight_live, axis=1), use_container_width=True)
