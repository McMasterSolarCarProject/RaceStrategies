import sqlite3
import os
from .parse_kml import parse_kml_file
from .speed_limits import get_speed_limits, lookup_speed_limit
from .route_row import RouteRow, create_route_row_table_sql, insert_route_row_sql, validate_route_row_schema
import time
from ..engine.nodes import Segment

def init_route_db(db_path: str = "ASC_2024.sqlite", remake: bool = False, kml_path: str = "data/ASC_2024.kml") -> None:
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
        
        placemarks = parse_kml_file(kml_path)

        with sqlite3.connect(db_path) as connection:
            cursor = connection.cursor()
            create_route_table(cursor)
            populate_table(placemarks, cursor)

        print("Route data initialized.")
    else:
        with sqlite3.connect(db_path) as connection:
            validate_route_row_schema(connection.cursor())
        print(f"Database exists Already: {db_path}")
    

def create_route_table(cursor: sqlite3.Cursor) -> None:
    """
    Creates route_row table from RouteRow schema contract.
    """
    cursor.executescript(create_route_row_table_sql())
    validate_route_row_schema(cursor)


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
        cursor.executemany(insert_route_row_sql(), params)


def build_rows(placemark_name: str, coords: list, speed_limits: list) -> list[RouteRow]:
    rows: list[RouteRow] = []
    limit_index = 0
    total_distance = 0
    for coord_index, coord in enumerate(coords[:-1]):
        segment = Segment(coord, coords[coord_index + 1])
        total_distance += segment.dist

        speed_limit, limit_index = lookup_speed_limit(speed_limits, total_distance, limit_index)
        rows.append(RouteRow(placemark_name=placemark_name, id=coord_index, lat=coord.lat, lon=coord.lon, elevation=coord.elevation, distance=total_distance, speed_limit=speed_limit, stop_type=None, ghi=None, wind_dir=None, wind_speed=None, speed=-1, torque=-1))
    rows.append(RouteRow(placemark_name=placemark_name, id=rows[-1].id + 1, lat=coords[-1].lat, lon=coords[-1].lon, elevation=coords[-1].elevation, distance=total_distance, speed_limit=0, stop_type=True, ghi=None, wind_dir=None, wind_speed=None, speed=-1, torque=-1))
    return rows

if __name__ == "__main__":
    print("Started Route DB Initialization")
    start = time.time()
    init_route_db(remake= True)
    print(f"Finished creating Database: {time.time()-start}")
