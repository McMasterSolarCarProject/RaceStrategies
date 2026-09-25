import argparse
import time

from .init_route_table import init_route_db
from .parse_kml import parse_kml_route
from .speed_limits import update_speed_limits_from_csv
from .traffic import update_traffic


def main(route_name: str, remake: bool = False) -> None:
    route_db_path = f"{route_name}.sqlite"
    kml_path = f"data/{route_name}.kml"
    start = time.perf_counter()

    print("Starting Database Generation...")
    print(f"  Database path: {route_db_path}")
    print(f"  KML path: {kml_path}")
    init_route_db(route_db_path, kml_path, remake=remake)
    print(f"Database initialized in {time.perf_counter()-start:.2f}s\n")

    print("Updating additional data for placemarks...")
    placemarks = parse_kml_route(kml_path)

    for i, placemark in enumerate(placemarks, 1):
        print(f"Updating placemark {i}/{len(placemarks)}: {placemark}")
        update_speed_limits_from_csv(placemark, db_path=route_db_path)

    # print("Updating traffic data...")
    # update_traffic("A. Independence to Topeka", db_path=route_db_path)

    print(f"\nCompleted in {time.perf_counter()-start:.2f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize a route database from a route name.")
    parser.add_argument("route_name", help="Route name used for the SQLite and KML filenames")
    parser.add_argument("--remake", action="store_true",help="Delete and recreate the database if it already exists")
    args = parser.parse_args()
    main(args.route_name, args.remake)
    