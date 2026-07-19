from ...database.init_route_table import init_route_db
from ...database.parse_kml import parse_kml_file
from ...database.speed_limits import update_speed_limits_from_csv, update_curvature_speed_limits
from ...database.update_velocity import update_target_velocity


def upload_kml(kml_path: str) -> str:
    """
    Backend function that uses the uploaded kml file to populate the sqlite file
    """
    db_path = kml_path.replace(".kml", ".sqlite")
    init_route_db(db_path=db_path, remake=False, kml_path=kml_path)  # set this to true to remake database each time

    placemarks = parse_kml_file(kml_path)

    for i, placemark in enumerate(placemarks, 1):
        print(f"Updating placemark {i}/{len(placemarks)}: {placemark}")
        update_speed_limits_from_csv(placemark, db_path=db_path)
        update_curvature_speed_limits(placemark, db_path=db_path)
        update_target_velocity(placemark, db_path=db_path)

    return db_path
