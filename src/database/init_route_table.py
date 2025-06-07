import sqlite3
import datetime
import csv
import os
from .parse_route import parse_ASC2024, parse_FSGP_2025, calc_distance, calc_azimuth
import time
from .traffic import overpass_batch_request, generate_boundary, priority_stop


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
        placemarks = [parse_ASC2024()[0]] #rigged
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

def populate_table(placemarks, cursor):  # Make this better and Document
    print(f"Generating Route data")

    for segment, placemark in enumerate(placemarks):
        print(placemark.name)
        with open(f"data/limits/{placemark.name} Limits.csv", "r") as file:
            reader = csv.reader(file)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]

        data = []
        limit_index = 0
        for coord_index, c in enumerate(placemark.coords):
            dist = calc_distance(placemark.coords, c)
            while speed_limits[limit_index][0] <= dist:
                limit_index += 1

            # traffic
            bbox = generate_boundary(c.lat, c.lon)
            coord_data = overpass_batch_request(bbox)
            stop = None
            if coord_data:
                stop = priority_stop(coord_data)[0]
                print(coord_index,stop)

            data.append([placemark.name, coord_index, c.lat, c.lon, c.elevation * 0.3048, dist,
                         speed_limits[limit_index - 1][1], stop, None, None, None, 100, 100])
        
        # run batch stuff here 
        column_count = ",".join(["?"] * len(data[0]))
        cursor.executemany(f"insert into route_data values ({column_count})", data)


if __name__ == "__main__":
    start = time.time()
    init_route_db()
    print(time.time()-start)
