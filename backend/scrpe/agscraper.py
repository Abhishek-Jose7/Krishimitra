import requests
import pandas as pd
import sqlite3
import io
import time
import logging
from datetime import date, datetime


# ==========================================================
# ======================= CONFIG ===========================
# ==========================================================

STATE_ID        = 16
STATE_NAME      = "Karnataka"

COMMODITY_ID    = 2
COMMODITY_NAME  = "Paddy(Common)"

LIVE_DATE       = "2025-11-07"
START_YEAR      = 2021

DB_PATH         = "kpaddyprices.db"

REQUEST_DELAY   = 2
RETRY_ATTEMPTS  = 5


# ==========================================================
# ======================= LOGGING ==========================
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("price.log"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)


# ==========================================================
# ==================== SCRAPER CLASS =======================
# ==========================================================

class AgmarknetScraper:

    def __init__(self):

        self.base_api = (
            "https://api.agmarknet.gov.in/v1/prices-and-arrivals"
            "/date-wise/specific-commodity"
        )

        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "origin": "https://www.agmarknet.gov.in",
            "referer": "https://www.agmarknet.gov.in/",
            "user-agent": "Mozilla/5.0"
        })

        self._init_db()

    # ------------------------------------------------------

    def _init_db(self):

        with sqlite3.connect(DB_PATH) as conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY,
                    market TEXT NOT NULL,
                    state TEXT NOT NULL,
                    commodity TEXT NOT NULL,
                    arrival_date DATE NOT NULL,
                    arrival_quantity REAL,
                    variety TEXT,
                    min_price REAL,
                    max_price REAL,
                    modal_price REAL,
                    UNIQUE(market, commodity, arrival_date)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_prices_market_date
                ON prices(market, arrival_date)
            """)

    # ------------------------------------------------------

    def _get_resume_date(self):

        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("""
                SELECT MAX(arrival_date)
                FROM prices
                WHERE commodity = ?
            """, (COMMODITY_NAME,)).fetchone()

        if row and row[0]:
            return datetime.strptime(row[0], "%Y-%m-%d")

        return None

    # ------------------------------------------------------

    def _next_month(self, dt):

        return datetime(
            dt.year + (dt.month // 12),
            (dt.month % 12) + 1,
            1
        )

    # ------------------------------------------------------

    def _safe_float(self, x):

        try:
            return float(str(x).replace(",", "").strip())
        except:
            return None

    # ------------------------------------------------------

    def _download_month(self, year, month):

        params = {
            "year": year,
            "month": str(month).zfill(2),
            "stateId": STATE_ID,
            "commodityId": COMMODITY_ID,
            "includeCsv": "true"
        }

        if LIVE_DATE:
            params["liveDate"] = LIVE_DATE

        for attempt in range(RETRY_ATTEMPTS):

            try:
                r = self.session.get(
                    self.base_api,
                    params=params,
                    timeout=30
                )

                if r.status_code == 200:
                    return r.text

                log.warning(f"Attempt {attempt+1}: HTTP {r.status_code}")

            except Exception as e:
                log.warning(f"Attempt {attempt+1} failed: {e}")

            time.sleep(2)

        return None

    # ------------------------------------------------------

    def _parse_csv(self, csv_text):

        lines = csv_text.splitlines()

        header_idx = next(
            (i for i, l in enumerate(lines)
             if "Arrival Date" in l),
            None
        )

        if header_idx is None:
            return pd.DataFrame()

        df = pd.read_csv(
            io.StringIO("\n".join(lines[header_idx:])),
            engine="python",
            on_bad_lines="skip"
        )

        df.columns = df.columns.str.strip()

        rows = []
        current_market = None

        for _, row in df.iterrows():

            first = str(row.get("Arrival Date", "")).strip()

            if first.startswith("Market Name"):
                current_market = first.replace(
                    "Market Name :", ""
                ).strip()
                continue

            arrival = pd.to_datetime(
                first,
                dayfirst=True,
                errors="coerce"
            )

            if pd.isna(arrival) or current_market is None:
                continue

            rows.append({
                "market": current_market,
                "state": STATE_NAME,
                "commodity": COMMODITY_NAME,
                "arrival_date": arrival.date().isoformat(),
                "arrival_quantity": self._safe_float(
                    row.get("Arrivals (Metric Tonnes)")
                ),
                "variety": row.get("Variety"),
                "min_price": self._safe_float(
                    row.get("Minimum Price (Rs./Quintal)")
                ),
                "max_price": self._safe_float(
                    row.get("Maximum Price (Rs./Quintal)")
                ),
                "modal_price": self._safe_float(
                    row.get("Modal Price (Rs./Quintal)")
                )
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------

    def _save_prices(self, df):

        if df.empty:
            return 0

        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany("""
                INSERT OR IGNORE INTO prices
                (market, state, commodity,
                 arrival_date, arrival_quantity,
                 variety,
                 min_price, max_price, modal_price)
                VALUES
                (:market, :state, :commodity,
                 :arrival_date, :arrival_quantity,
                 :variety,
                 :min_price, :max_price, :modal_price)
            """, df.to_dict("records"))

        return len(df)

    # ------------------------------------------------------

    def run(self):

        resume = self._get_resume_date()

        if resume:
            current = self._next_month(resume)
            log.info(f"Resuming from {current.strftime('%Y-%m')}")
        else:
            current = datetime(START_YEAR, 1, 1)
            log.info(f"Starting fresh from {current.strftime('%Y-%m')}")

        end = datetime(
            date.today().year,
            date.today().month,
            1
        )

        while current <= end:

            year  = current.year
            month = current.month

            log.info(f"Fetching {year}-{month:02d}")

            csv_text = self._download_month(year, month)

            if csv_text:
                df = self._parse_csv(csv_text)
                saved = self._save_prices(df)
                log.info(f" → {saved} rows inserted")

            time.sleep(REQUEST_DELAY)
            current = self._next_month(current)

        log.info("Price scraping complete.")


# ==========================================================

if __name__ == "__main__":
    scraper = AgmarknetScraper()
    scraper.run()