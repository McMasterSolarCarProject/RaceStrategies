import sqlite3
import csv
import os
from .parse_kml import parse_kml_file
import time
from ..engine.nodes import Segment
# from .curvature_speed_limit import update_curvature_speed_limits
# from .traffic import update_traffic
# from .update_velocity import update_target_velocity

def init_route_db(db_path: str = "data.sqlite", schema_path: str = "route_data.sql", remake: bool = False, kml_path: str = "data/Main Route.kml") -> None:
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
            create_route_table(cursor, schema_path)
            populate_table(placemarks, cursor)

        print("Route data initialized.")
    else:
        print(f"Database exists Already: {db_path}")
    

def create_route_table(cursor: sqlite3.Cursor, schema_path: str = "route_data.sql") -> None:
    """
    Reads and executes SQL schema for the route_data table.
    """
    abs_path = os.path.join(os.path.dirname(__file__), schema_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Schema file not found: {abs_path}")

    with open(abs_path, "r") as f:
        schema_sql = f.read()
        cursor.executescript(schema_sql)


def populate_table(placemarks: dict, cursor: sqlite3.Cursor) -> None:  # Make this better and Document
    """
    Populate route_data table with segment data and speed limits.
    - If speed limit CSV is missing, rows are inserted with speed = NULL and marked as speed_unknown.
    """
    print(f"Populating route data for {len(placemarks)} placemarks...")
    for placemark_name, coords in placemarks.items():
        print(f"Processing: {placemark_name}")
        speed_limits = get_speed_limits(placemark_name)
        data = build_rows(placemark_name, coords, speed_limits)

        column_count = ",".join(["?"] * len(data[0]))
        cursor.executemany(f"insert into route_data values ({column_count})", data)

def get_speed_limits(placemark_name: str) -> list:
    limits_path = f"data/limits/{placemark_name} Limits.csv"
    if os.path.exists(limits_path):
        with open(limits_path, "r") as file:
            reader = csv.reader(file)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]
        speed_limits.sort(key=lambda x: x[0])  # Ensures all speed limit data is sorted in order of index
    else:
        print(f"WARNING: Missing speed limits for {placemark_name}")
        speed_limits = []
    return speed_limits
    

def build_rows(placemark_name: str, coords: list, speed_limits: list) -> list:
    data = []
    limit_index = 0
    tdist = 0
    for coord_index, c in enumerate(coords[:-1]):
        s = Segment(c, coords[coord_index + 1])
        tdist += s.dist
        # dist = calc_distance(placemarks[placemark_name], c)
        if len(speed_limits) > 0:
            while limit_index + 1 < len(speed_limits) and speed_limits[limit_index][0] <= tdist:
                limit_index += 1
            speed_limit = speed_limits[limit_index][1]
        else:
            speed_limit = -1  # value to indicate missing speed limit

        data.append([placemark_name, coord_index, c.lat, c.lon, c.elevation, tdist, speed_limit, None, None, None, None, -1, -1])
    data.append([placemark_name, data[-1][1] + 1, coords[-1].lat, coords[-1].lon, coords[-1].elevation, tdist, 0, True, None, None, None, -1, -1])
    return data

if __name__ == "__main__":
    print("Started Route DB Initialization")
    start = time.time()
    init_route_db(remake= True)
    print(f"Finished creating Database: {time.time()-start}")
