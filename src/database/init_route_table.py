import sqlite3
import os
from .parse_kml import parse_kml_route
from .route_table import RouteRow, RouteTable
from .speed_limits import get_speed_limits, lookup_speed_limit
from ..models import Coordinate, Displacement

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
            RouteTable.create_table(cursor)
            RouteTable.validate_schema(cursor)
            populate_table(placemarks, cursor)

        print("Route data initialized.")
    else:
        with sqlite3.connect(db_path) as connection:
            RouteTable.validate_schema(connection.cursor())
        print(f"Database exists Already: {db_path}")


def populate_table(placemarks: dict, cursor: sqlite3.Cursor) -> None:  # Make this better and Document
    """
    Populate route_table with segment data and speed limits.
    - If speed limit CSV is missing, rows are inserted with speed = NULL and marked as speed_unknown.
    """
    print(f"Populating route data for {len(placemarks)} placemarks...")
    for placemark_name, coords in placemarks.items():
        print(f"Processing: {placemark_name}")
        speed_limits = get_speed_limits(placemark_name)
        rows = init_rows(placemark_name, coords, speed_limits)
        params = [r.to_db_params() for r in rows]
        cursor.executemany(RouteTable.insert_sql(), params)

def init_rows(placemark_name: str, coords: list[Coordinate], speed_limits: list) -> list[RouteRow]:
    rows: list[RouteRow] = []
    limit_index = 0
    total_distance = 0
    for coord_index, coord in enumerate(coords[:-1]):
        total_distance += Displacement(coord, coords[coord_index + 1]).dist

        speed_limit, limit_index = lookup_speed_limit(speed_limits, total_distance, limit_index)
        rows.append(RouteRow(placemark_name=placemark_name, id=coord_index, lat=coord.lat, lon=coord.lon, elevation=coord.elevation, distance=total_distance, speed_limit=speed_limit))
    rows.append(RouteRow(placemark_name=placemark_name, id=rows[-1].id + 1, lat=coords[-1].lat, lon=coords[-1].lon, elevation=coords[-1].elevation, distance=total_distance, speed_limit=0))
    return rows


if __name__ == "__main__":
    import time
    print("Started Route DB Initialization")
    start = time.time()
    init_route_db("ASC_2024.sqlite", "data/ASC_2024.kml", remake= True)
    print(f"Finished creating Database: {time.time()-start}")
