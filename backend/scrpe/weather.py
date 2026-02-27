import sqlite3
import requests
import pandas as pd
import time
import logging
import re
from datetime import datetime

DB_PATH = "kpaddyprices.db"
RETRY_ATTEMPTS = 5
API_URL = "https://archive-api.open-meteo.com/v1/archive"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("weather.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------
# CLEANING LOGIC (same as markets.py)
# ---------------------------------------------------------

NOISE_PATTERN = re.compile(
    r'\b(apmc|vfpck|apcos|market|mandi|yard|regulated|agricultural|co-op|cooperative|ltd)\b',
    flags=re.IGNORECASE
)

def clean_market_name(market_name):
    cleaned = re.sub(r'\(.*?\)', '', market_name)
    cleaned = NOISE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()

# ---------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------

def init_weather_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY,
                market TEXT NOT NULL,
                date DATE NOT NULL,
                precipitation_mm REAL,
                temp_max_c REAL,
                temp_min_c REAL,
                temp_avg_c REAL,
                rain_7d_rolling REAL,
                UNIQUE(market, date)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_market_date
            ON weather(market, date)
        """)

# ---------------------------------------------------------
# RANGE CHECK
# ---------------------------------------------------------

def range_complete(market, start, end):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT COUNT(DISTINCT date)
            FROM weather
            WHERE market = ? AND date BETWEEN ? AND ?
        """, (market, start, end)).fetchone()

    expected = (
        datetime.strptime(end, "%Y-%m-%d") -
        datetime.strptime(start, "%Y-%m-%d")
    ).days + 1

    return row[0] >= expected

# ---------------------------------------------------------
# GET MARKETS WITH COORDS
# ---------------------------------------------------------

def get_markets_with_coords():
    with sqlite3.connect(DB_PATH) as conn:
        raw_markets = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT market FROM prices"
            )
        ]

        coords_map = {
            r[0]: (r[1], r[2]) for r in conn.execute(
                "SELECT clean_name, latitude, longitude FROM markets"
            )
        }

    result = []
    skipped = []

    for market in raw_markets:
        clean = clean_market_name(market)
        if clean in coords_map and coords_map[clean][0] is not None:
            lat, lon = coords_map[clean]
            result.append((market, lat, lon))
        else:
            skipped.append(market)

    if skipped:
        log.warning(f"Skipping {len(skipped)} markets with no coordinates:")
        for m in skipped:
            log.warning(f"  - {m}")

    return result

# ---------------------------------------------------------
# FETCH WEATHER
# ---------------------------------------------------------

def fetch_weather(market, lat, lon, start, end):

    if range_complete(market, start, end):
        log.info(f"  Already complete: {market}")
        return 0

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Kolkata"
    }

    data = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            r = requests.get(API_URL, params=params, timeout=30)

            if r.status_code == 200:
                data = r.json()
                break
            else:
                log.warning(f"  Attempt {attempt}: HTTP {r.status_code}")

        except Exception as e:
            log.warning(f"  Attempt {attempt} error: {e}")

        if r.status_code == 429:
            sleep_time = 5 * attempt
        else:
            sleep_time = 2

        time.sleep(sleep_time)

    if not data:
        log.error(f"  Failed after {RETRY_ATTEMPTS} attempts: {market}")
        return 0

    daily = data.get("daily", {})
    if "time" not in daily:
        log.error(f"  No daily data returned for {market}")
        return 0

    df = pd.DataFrame({
        "market": market,
        "date": daily["time"],
        "precipitation_mm": daily["precipitation_sum"],
        "temp_max_c": daily["temperature_2m_max"],
        "temp_min_c": daily["temperature_2m_min"],
    })

    df["temp_avg_c"] = (df["temp_max_c"] + df["temp_min_c"]) / 2
    df["rain_7d_rolling"] = df["precipitation_mm"].rolling(7, min_periods=1).sum()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO weather
            (market, date, precipitation_mm,
             temp_max_c, temp_min_c,
             temp_avg_c, rain_7d_rolling)
            VALUES
            (:market, :date, :precipitation_mm,
             :temp_max_c, :temp_min_c,
             :temp_avg_c, :rain_7d_rolling)
        """, df.to_dict("records"))

    return len(df)

# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------

def run():
    init_weather_table()

    with sqlite3.connect(DB_PATH) as conn:
        start_date, end_date = conn.execute("""
            SELECT MIN(arrival_date), MAX(arrival_date)
            FROM prices
        """).fetchone()

    if not start_date or not end_date:
        log.error("No price data found.")
        return

    log.info(f"Fetching weather from {start_date} to {end_date}")

    markets = get_markets_with_coords()
    log.info(f"Total markets: {len(markets)}")

    for i, (market, lat, lon) in enumerate(markets, 1):
        log.info(f"[{i}/{len(markets)}] {market} ({lat:.4f}, {lon:.4f})")
        inserted = fetch_weather(market, lat, lon, start_date, end_date)
        log.info(f"  -> {inserted} rows inserted")
        time.sleep(0.8)

    log.info("Weather pipeline complete.")
    log.info("You can now join: prices.market = weather.market AND prices.arrival_date = weather.date")

# ---------------------------------------------------------

if __name__ == "__main__":
    run()