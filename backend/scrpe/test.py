import sqlite3

DB_PATH = "kgingerprices.db"

with sqlite3.connect(DB_PATH) as conn:

    # List all tables
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]

    print(f"Tables in {DB_PATH}: {tables}\n")
    print("=" * 60)

    for table in tables:
        # Row count
        count = conn.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]

        # Column names
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info('{table}')")]

        print(f"\nTable: {table}")
        print(f"  Rows    : {count:,}")
        print(f"  Columns : {cols}")

        # Sample rows
        rows = conn.execute(f"SELECT * FROM '{table}' LIMIT 20").fetchall()
        print(f"  Sample  :")
        for row in rows:
            print(f"    {row}")

    print("\n" + "=" * 60)