import os
import sqlite3

DB_PATH = "data.sqlite"

def db_exists(path: str = DB_PATH) -> bool:
    return os.path.exists(path)

def get_segment_ids(path: str = DB_PATH) -> list[str]:
    if not db_exists(path):
        raise FileNotFoundError(f"Could not find database file {path}")

    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT placemark_name FROM route_data WHERE placemark_name IS NOT NULL")
        segment_ids = sorted(row[0] for row in cur.fetchall())
    conn.close()  # With block doesn't automatically close sqlite connection
    return segment_ids
