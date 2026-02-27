import sqlite3
import pandas as pd

DB_PATH = "kpaddyprices.db"

with sqlite3.connect(DB_PATH) as conn:

    df = pd.read_sql_query("""
        SELECT
            p.arrival_date,
            p.market,
            p.state,
            p.commodity,
            p.arrival_quantity,
            p.variety,
            p.min_price,
            p.max_price,
            p.modal_price,
            w.temp_max_c,
            w.temp_min_c,
            w.temp_avg_c,
            w.precipitation_mm,
            w.rain_7d_rolling
        FROM prices p
        LEFT JOIN weather w
            ON p.market = w.market
           AND p.arrival_date = w.date
    """, conn)

    print("Joined rows :", len(df))
    print("Date range  :", df["arrival_date"].min(), "to", df["arrival_date"].max())
    print("Markets     :", df["market"].nunique())

    print("\nMissing values:")
    print(df.isna().sum())

    print("\nSample:")
    print(df.head(10))

    # SAVE TO NEW TABLE
    df.to_sql("model_data", conn, if_exists="replace", index=False)

print("\nTable 'model_data' created successfully.")