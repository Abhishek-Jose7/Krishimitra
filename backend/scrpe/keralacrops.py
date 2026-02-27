import requests
import pandas as pd
import sqlite3
import io
import time
import logging
from datetime import date, datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)


class AgmarknetScraper:

    def __init__(self, state_id, commodity_id, commodity_name, state_name, db_path):
        self.base_api = "https://api.agmarknet.gov.in/v1/prices-and-arrivals/date-wise/specific-commodity"
        self.state_id = state_id
        self.commodity_id = commodity_id
        self.commodity_name = commodity_name
        self.state_name = state_name
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.agmarknet.gov.in/"
        })
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id           INTEGER PRIMARY KEY,
                    market       TEXT NOT NULL,
                    state        TEXT,
                    commodity    TEXT NOT NULL,
                    arrival_date DATE NOT NULL,
                    min_price    REAL,
                    max_price    REAL,
                    modal_price  REAL,
                    UNIQUE(market, commodity, arrival_date)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_date ON prices(market, arrival_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_commodity_date ON prices(commodity, arrival_date)")

    def _get_resume_date(self):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT MAX(arrival_date) FROM prices WHERE commodity = ?",
                (self.commodity_name,)
            ).fetchone()
        val = row[0] if row else None
        return datetime.strptime(val, "%Y-%m-%d") if val else None

    def _next_month(self, dt):
        return datetime(dt.year + (dt.month // 12), (dt.month % 12) + 1, 1)

    def _safe_float(self, x):
        try:
            return float(str(x).replace(",", "").strip())
        except (ValueError, AttributeError):
            return None

    def _download_month(self, year, month):
        params = {
            "year": year,
            "month": str(month).zfill(2),
            "stateId": self.state_id,
            "commodityId": self.commodity_id,
            "liveDate": date.today().strftime("%Y-%m-%d"),
            "includeCsv": "true"
        }
        for attempt in range(5):
            try:
                r = self.session.get(self.base_api, params=params, timeout=30)
                if r.status_code == 200:
                    return r.text
                log.warning(f"{year}-{month:02d}: HTTP {r.status_code}")
            except requests.RequestException as e:
                log.warning(f"{year}-{month:02d} attempt {attempt+1} failed: {e}")
                time.sleep(3 * (attempt + 1))
        log.error(f"Giving up on {year}-{month:02d}")
        return None

    def _parse_csv(self, csv_text):
        # Find the actual header row dynamically
        lines = csv_text.splitlines()
        header_idx = next(
            (i for i, l in enumerate(lines) if "Arrival Date" in l),
            None
        )
        if header_idx is None:
            log.warning("Could not find header row in CSV")
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
                current_market = first.replace("Market Name :", "").strip()
                continue

            arrival = pd.to_datetime(first, dayfirst=True, errors="coerce")
            if pd.isna(arrival) or current_market is None:
                continue

            rows.append({
                "market":       current_market,
                "state":        self.state_name,
                "commodity":    self.commodity_name,
                "arrival_date": arrival.date().isoformat(),
                "min_price":    self._safe_float(row.get("Minimum Price (Rs./Quintal)")),
                "max_price":    self._safe_float(row.get("Maximum Price (Rs./Quintal)")),
                "modal_price":  self._safe_float(row.get("Modal Price (Rs./Quintal)")),
            })

        return pd.DataFrame(rows)

    def _save_to_db(self, df):
        if df.empty:
            return 0
        with sqlite3.connect(self.db_path) as conn:
            # INSERT OR REPLACE handles dedup at write time
            conn.executemany("""
                INSERT OR REPLACE INTO prices
                    (market, state, commodity, arrival_date, min_price, max_price, modal_price)
                VALUES
                    (:market, :state, :commodity, :arrival_date, :min_price, :max_price, :modal_price)
            """, df.to_dict("records"))
        return len(df)

    def run(self, start_year):
        resume = self._get_resume_date()
        current = self._next_month(resume) if resume else datetime(start_year, 1, 1)
        end = datetime(date.today().year, date.today().month, 1)

        log.info(f"Starting from {current.strftime('%Y-%m')}, end: {end.strftime('%Y-%m')}")

        while current <= end:
            year, month = current.year, current.month
            log.info(f"Fetching {year}-{month:02d}")

            csv_text = self._download_month(year, month)
            if csv_text:
                df = self._parse_csv(csv_text)
                saved = self._save_to_db(df)
                log.info(f"  → {saved} rows saved")

            time.sleep(2)
            current = self._next_month(current)

        log.info("Scraping complete.")