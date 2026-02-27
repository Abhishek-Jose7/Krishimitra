import sqlite3
import requests
import time
import re

DB_PATH = "kpaddyprices.db"

# Words to strip from market names
NOISE_PATTERN = re.compile(
    r'\b(APMC|VFPCK|apcos|market|mandi|yard|regulated|agricultural|co-op|cooperative|ltd)\b',
    flags=re.IGNORECASE
)

def clean_market_name(market_name):
    """Strip noise words and parenthetical content, return clean town name."""
    cleaned = re.sub(r'\(.*?\)', '', market_name)   # remove (EEC), (1) etc.
    cleaned = NOISE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()

def is_in_karnataka(lat, lon):
    return 11.5 <= lat <= 18.5 and 74.0 <= lon <= 78.5

def geocode_photon(place_name, state="Karnataka"):
    """Photon geocoder — fast, free, no API key needed."""
    try:
        r = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": f"{place_name}, {state}, India", "limit": 5},
            headers={"User-Agent": "coconut-price-scraper"},
            timeout=15
        )
        data = r.json()
        features = data.get("features", [])
        # Pick first result that falls inside Karnataka
        for feature in features:
            lon, lat = feature["geometry"]["coordinates"]
            if is_in_karnataka(lat, lon):
                return lat, lon
        # If nothing in Karnataka, return None so Nominatim can try
    except Exception as e:
        print(f"  ! Photon error: {e}")
    return None, None

def geocode_nominatim(place_name, state="Kerala, India"):
    """Nominatim fallback."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{place_name}, {state}", "format": "json", "limit": 1},
            headers={"User-Agent": "coconut-price-scraper"},
            timeout=20
        )
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        print(f"  ! Nominatim error: {e}")
    return None, None

def geocode(place_name):
    """Try Photon first, fall back to Nominatim."""
    lat, lon = geocode_photon(place_name)
    if lat is not None:
        return lat, lon
    print(f"  ! Photon failed, trying Nominatim...")
    time.sleep(1)
    return geocode_nominatim(place_name)

def populate_market_locations(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                clean_name TEXT PRIMARY KEY,
                latitude   REAL,
                longitude  REAL
            )
        """)

        markets = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT market FROM prices"
            )
        ]

    print(f"Found {len(markets)} distinct markets.\n")

    # Cache clean_name → (lat, lon) to skip duplicate API calls
    geocode_cache = {}

    # Pre-load already-geocoded entries into cache
    with sqlite3.connect(db_path) as conn:
        for row in conn.execute(
            "SELECT clean_name, latitude, longitude FROM markets WHERE latitude IS NOT NULL"
        ):
            geocode_cache[row[0]] = (row[1], row[2])

    for market in markets:
        clean = clean_market_name(market)

        # Skip entirely if this town is already in DB or cache
        if clean in geocode_cache:
            print(f"Skipping '{market}' → '{clean}' (already geocoded)")
            continue

        print(f"Processing : {market}")
        print(f"  → Cleaned : {clean}")

        lat, lon = geocode(clean)
        print(f"  → Coords  : {lat}, {lon}")

        if lat is not None:
            geocode_cache[clean] = (lat, lon)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO markets (clean_name, latitude, longitude)
                VALUES (?, ?, ?)
            """, (clean, lat, lon))

        time.sleep(1.2)

    print("\nDone. Summary:\n")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT clean_name, latitude, longitude FROM markets ORDER BY clean_name"
        ).fetchall()

    print(f"{'Town':<25} {'Lat':>12} {'Lon':>12}")
    print("-" * 52)
    failed = []
    for clean, lat, lon in rows:
        lat_str = f"{lat:.4f}" if lat else "FAILED"
        lon_str = f"{lon:.4f}" if lon else "FAILED"
        print(f"{clean:<25} {lat_str:>12} {lon_str:>12}")
        if not lat:
            failed.append(clean)

    if failed:
        print(f"\n{len(failed)} towns need manual coordinates:")
        for m in failed:
            print(f"  - {m}")
        print("\nFix with:")
        print("  UPDATE markets SET latitude=xx.xxxx, longitude=yy.yyyy WHERE clean_name='...'")

if __name__ == "__main__":
    populate_market_locations(DB_PATH)