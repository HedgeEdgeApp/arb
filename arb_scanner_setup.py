# 🔍 Arbitrage Betting Scanner (Updated Web Scraping Version)

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
SPORT_URLS = {
    "soccer": "https://www.oddsportal.com/football/",
    "tennis": "https://www.oddsportal.com/tennis/",
    "basketball": "https://www.oddsportal.com/basketball/",
    "mma": "https://www.oddsportal.com/mma/",
    "baseball": "https://www.oddsportal.com/baseball/"
}

# === Streamlit Setup ===
st.set_page_config(page_title="Free Arbitrage Scanner", layout="wide")
st.title("📈 Free Arbitrage Betting Scanner (Multi-Sport Snapshot)")

col1, col2 = st.columns([3, 1])
with col1:
    min_margin = st.slider("Minimum Arbitrage Margin (%)", 0.0, 10.0, 0.5, 0.1)
with col2:
    refresh = st.checkbox("🔄 Refresh Odds", value=True)

@st.cache_data(ttl=900)
def scrape_all_sports():
    all_events = []
    now_nz = datetime.now(NZ_TZ)

    for sport, url in SPORT_URLS.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.content, "html.parser")

            matches = soup.select("div.eventRow")
            for match in matches:
                try:
                    name_tag = match.select_one("div.participantBox span")
                    if not name_tag:
                        continue
                    name = name_tag.get_text(strip=True)

                    odds_tags = match.select("div.odds span.oddsValue")
                    odds = [float(odds.get_text(strip=True)) for odds in odds_tags if re.match(r"^[0-9]+\.[0-9]+$", odds.get_text(strip=True))]
                    if len(odds) < 2:
                        continue

                    time_tag = match.select_one("div.eventTime")
                    if time_tag and re.match(r"\d{2}:\d{2}", time_tag.get_text(strip=True)):
                        hour, minute = map(int, time_tag.get_text(strip=True).split(":"))
                        start_dt = now_nz.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if start_dt < now_nz:
                            start_dt += timedelta(days=1)
                    else:
                        start_dt = now_nz

                    inv_sum = sum(1 / o for o in odds[:2])
                    arb_margin = (1 - inv_sum) * 100 if inv_sum < 1 else 0

                    all_events.append({
                        "Match": name,
                        "Sport": sport.title(),
                        "Odds 1": odds[0],
                        "Odds 2": odds[1],
                        "Arb Margin (%)": round(arb_margin, 2),
                        "Start Time (NZT)": start_dt.strftime("%Y-%m-%d %H:%M"),
                        "Countdown": "LIVE" if start_dt <= now_nz else str(start_dt - now_nz).split(".")[0],
                        "Live": start_dt <= now_nz
                    })
                except:
                    continue
        except:
            continue

    return all_events

# === Main Logic ===
if refresh:
    with st.spinner("Scraping odds from multiple sports (OddsPortal)..."):
        data = scrape_all_sports()
        if not data:
            st.warning("No events found. OddsPortal may be offline or blocking access.")
        else:
            df = pd.DataFrame(data)
            df = df[df["Arb Margin (%)"] >= min_margin]
            df = df.sort_values(by=["Live", "Start Time (NZT)"], ascending=[False, True])

            if df.empty:
                st.info("No arbitrage opportunities found above the selected margin.")
            else:
                def highlight_live(row):
                    return ["background-color: #ffdddd" if row.Live else "" for _ in row]

                st.success(f"Found {len(df)} arbitrage opportunities across sports!")
                st.dataframe(df.style.apply(highlight_live, axis=1), use_container_width=True)
