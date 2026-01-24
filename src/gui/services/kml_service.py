from ...database.init_route_table import init_route_db


def upload_kml(path: str) -> None:
    """
    Backend function that uses the uploaded kml file to populate the sqlite file
    """
    init_route_db(remake=False, kml_path=path)  # set this to true to remake database each time
