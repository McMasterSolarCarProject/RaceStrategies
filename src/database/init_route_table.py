import sqlite3
import os
from .parse_kml import parse_kml_route
from .route_row import RouteRow, build_rows
from .speed_limits import get_speed_limits

def init_route_db(db_path: str, kml_path: str, remake: bool = False) -> None:
    """
    Deletes the existing database, recreates schema, and populates route data.
    """

    if remake and os.path.exists(db_path):
        os.remove(db_path)
        print(f"Deleted existing database: {db_path}")

    if not os.path.exists(db_path):
        if not os.path.exists(kml_path):
            raise FileNotFoundError(f"KML path {kml_path} not found")
        if not kml_path.lower().endswith(".kml"):
            raise ValueError(f"File {kml_path} is not a KML file")
        
        placemarks = parse_kml_route(kml_path)

        with sqlite3.connect(db_path) as connection:
            cursor = connection.cursor()
            cursor.executescript(RouteRow.create_table_sql())
            RouteRow.validate_schema(cursor)
            populate_table(placemarks, cursor)

        print("Route data initialized.")
    else:
        with sqlite3.connect(db_path) as connection:
            RouteRow.validate_schema(connection.cursor())
        print(f"Database exists Already: {db_path}")


def populate_table(placemarks: dict, cursor: sqlite3.Cursor) -> None:  # Make this better and Document
    """
    Populate route_row table with segment data and speed limits.
    - If speed limit CSV is missing, rows are inserted with speed = NULL and marked as speed_unknown.
    """
    print(f"Populating route data for {len(placemarks)} placemarks...")
    for placemark_name, coords in placemarks.items():
        print(f"Processing: {placemark_name}")
        speed_limits = get_speed_limits(placemark_name)
        rows = build_rows(placemark_name, coords, speed_limits)
        params = [r.to_db_params() for r in rows]
        cursor.executemany(RouteRow.insert_sql(), params)



if __name__ == "__main__":
    import time
    print("Started Route DB Initialization")
    start = time.time()
    init_route_db("ASC_2024.sqlite", "data/ASC_2024.kml", remake= True)
    print(f"Finished creating Database: {time.time()-start}")
