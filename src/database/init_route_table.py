import sqlite3
import datetime
import csv
import os
from .parse_route import parse_ASC2024, parse_FSGP_2025
import time
from .traffic import overpass_batch_request, generate_boundary, priority_stops, regroup
from ..engine.nodes import Segment
from .curvature_speed_limit import upload_speed_limit
from .traffic import update_traffic

BATCH_SIZE = 50

def init_route_db(db_path: str = "data.sqlite", schema_path: str = "route_data.sql", remake = False, update_traffic_data = False) -> None:
    """
    Deletes the existing database, recreates schema, and populates route data.
    """
    if os.path.exists(db_path):
        if remake:
            os.remove(db_path)
            print(f"Deleted existing database: {db_path}")
        else:
            print(f"Database exists Already: {db_path}")
            return
    else:
        print("No existing database found.")

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        create_route_table(cursor, schema_path)
        placemarks = parse_ASC2024()
        populate_table(placemarks, cursor)
        connection.commit()
        print("Route data initialized.")
    
    for placemark in placemarks:
        print(f"Uploading speed limits for {placemark}")
        upload_speed_limit(placemark)

    if update_traffic_data:
        for placemark in placemarks:
            print(f"Updating traffic data for {placemark}")
            update_traffic(placemark)

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

def populate_table(placemarks: dict, cursor):  # Make this better and Document
    print(f"Generating Route data")

    for placemark in placemarks.keys():
        print(placemark)
        coords = placemarks[placemark]
        with open(f"data/limits/{placemark} Limits.csv", "r") as file:
            reader = csv.reader(file)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]

        data = []
        limit_index = 0
        tdist = 0
        for coord_index, c in enumerate(coords[:-1]):
            s = Segment(c, coords[coord_index + 1])
            tdist += s.dist
            # dist = calc_distance(placemarks[placemark], c)
            while speed_limits[limit_index][0] <= tdist:
                limit_index += 1

            # current = (c.lat, c.lon)
            stop = None
            # if (current in grouped and grouped[current]):
            #     stop = priority_stops({current: grouped[current]})[current]
            #     stop = stop.get('tags', {}).get('highway')


            data.append([placemark, coord_index, c.lat, c.lon, c.elevation, tdist, speed_limits[limit_index][1], stop, None, None, None, -1, -1])
            
        data.append([placemark, data[-1][1]+1, coords[-1].lat, coords[-1].lon, coords[-1].elevation, tdist, 0, True, None, None, None, -1, -1])
        # run batch stuff here 
        column_count = ",".join(["?"] * len(data[0]))
        cursor.executemany(f"insert into route_data values ({column_count})", data)


if __name__ == "__main__":
    print("Started Route DB Initialization")
    start = time.time()
    init_route_db(remake= False)
    print(f"Finished creating Database: {time.time()-start}")
