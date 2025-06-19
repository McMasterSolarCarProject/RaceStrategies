import sqlite3
import datetime
import csv
import os
from .parse_route import parse_ASC2024, parse_FSGP_2025, calc_distance
import time
from .traffic import overpass_batch_request, generate_boundary, priority_stops, regroup
from ..engine.kinematics import Coordinate, Displacement

BATCH_SIZE = 50

def init_route_db(db_path: str = "data.sqlite", schema_path: str = "route_data.sql") -> None:
    """
    Deletes the existing database, recreates schema, and populates route data.
    """
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Deleted existing database: {db_path}")
    else:
        print(f"No existing database found.")

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        create_route_table(cursor, schema_path)
        placemarks = {"A. Independence to Topeka":parse_ASC2024()["A. Independence to Topeka"]} #rigged
        populate_table(placemarks, cursor)
        connection.commit()
        print("Route data initialized.")


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

    for segment, placemark in enumerate(placemarks.keys()):
        print(placemark)
        with open(f"data/limits/{placemark} Limits.csv", "r") as file:
            reader = csv.reader(file)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]

        # traffic_data = []
        # coord_points = [Coordinate(c.lat, c.lon) for c in placemark.coords]
        # batch_bboxes = [generate_boundary(coord.lat, coord.lon) for coord in coord_points]
        # for i in range(0, len(batch_bboxes), BATCH_SIZE):
        #     batch = batch_bboxes[i:i+BATCH_SIZE]
        #     try:
        #         traffic_data.extend(overpass_batch_request(batch))
        #     except Exception as e:
        #         print(f"Error fetching batch: {e}")
        #         traffic_data.extend([None] for _ in batch)
        # grouped = regroup(traffic_data, coord_points)

        data = []
        limit_index = 0
        dist = 0
        for coord_index, c in enumerate(placemarks[placemark]):
            dist += c.dist
            print(dist)
            while speed_limits[limit_index][0] <= dist:
                limit_index += 1

            current = (c.lat, c.lon)
            stop = None
            # if (current in grouped and grouped[current]):
            #     stop = priority_stops({current: grouped[current]})[current]
            #     stop = stop.get('tags', {}).get('highway')


            data.append([placemark, coord_index, c.lat, c.lon, c.elevation, dist,
                         speed_limits[limit_index - 1][1], stop, None, None, None, 100, 100])
        
        # run batch stuff here 
        column_count = ",".join(["?"] * len(data[0]))
        cursor.executemany(f"insert into route_data values ({column_count})", data)


if __name__ == "__main__":
    start = time.time()
    init_route_db()
    print(time.time()-start)
