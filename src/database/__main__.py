from .init_route_table import init_route_db
from .parse_kml import parse_kml_file
from .speed_limits import update_speed_limits_from_csv, update_curvature_speed_limits
from .update_velocity import update_target_velocity
from .traffic import update_traffic

# Delete and Recreate the database
def main(route_db_path: str = "ASC_2024.sqlite", kml_path: str = "data/ASC_2024.kml"):
    import time
    start = time.perf_counter()
    
    print(f"Starting database initialization...")
    print(f"  Database path: {route_db_path}")
    print(f"  KML path: {kml_path}")
    init_route_db(db_path=route_db_path, kml_path=kml_path, remake= True)
    print(f"Database initialized in {time.perf_counter()-start:.2f}s\n")
    
    print(f"Updating additional data for placemarks...")
    placemarks = parse_kml_file(kml_path)
    
    for i, placemark in enumerate(placemarks, 1):
        print(f"Updating placemark {i}/{len(placemarks)}: {placemark}")
        update_speed_limits_from_csv(placemark)
        update_curvature_speed_limits(placemark)
        update_target_velocity(placemark)
        # update_traffic(placemark)
    
    print(f"\nCompleted in {time.perf_counter()-start:.2f}s")
    
if __name__ == "__main__":
    main()