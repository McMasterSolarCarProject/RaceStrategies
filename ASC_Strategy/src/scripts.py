import sqlite3
import datetime
import csv
from utils import parse_kml_file, calc_distance, calc_azimuth
import requests #only extra import
from classes import Coordinate

API_KEY = "CzhqptH0yb25zrdwdvji4u8AVPwKKHfJ" # 4
API_URL = "https://api.solcast.com.au/data/forecast/radiation_and_weather" # 4
SPEED = 55 # 4

# 4
def parse_isoformat(date_str):
    # Remove extra milliseconds and characters
    return datetime.datetime.fromisoformat(date_str.split(".")[0])

# 3
def get_irradiance_and_wind_data(
    coords: list[Coordinate], start_time: datetime.datetime
):
    coord_values = []
    current_time = start_time

    skip_every = 50
    prev_distance = 0

    for coord in coords[::skip_every]:
        new_distance = calc_distance(coords, coord)
        distance_delta = new_distance - prev_distance
        prev_distance = new_distance
        travel_time = datetime.timedelta(minutes=distance_delta / SPEED * 60)
        current_time += travel_time

        params = {
            "latitude": coord.lat,
            "longitude": coord.lon,
            "api_key": API_KEY,
            "format": "json",
            "hours": 10,  # Forecast horizon
            "period": "PT5M",  # Period length
            "output_parameters": "ghi,wind_direction_10m,wind_speed_10m",
        }
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            # Get the closest forecast period to the calculated arrival time
            forecasts = data["forecasts"]
            closest_forecast = min(
                forecasts,
                key=lambda x: abs(parse_isoformat(x["period_end"][:-1]) - current_time),
            )

            coord_values.extend(
                (
                    closest_forecast["ghi"],
                    closest_forecast["wind_direction_10m"],
                    closest_forecast["wind_speed_10m"],
                )
                for _ in range(skip_every)
            )
        else:
            coord_values.extend((0, 0, 0) for _ in range(skip_every))

    return coord_values

# 3
def data_rows(segment_id, db_data):
    final_data = []
    line_id = 0
    for i in db_data:
        line_id += 1
        final_data.append((segment_id, line_id) + i)
    return final_data


# 2
def generate_data(path_to_kml: str, current_time: datetime.datetime, cursor): # Make this better and Document
    print(f"[{path_to_kml}] Generating data...")
    placemarks = parse_kml_file(path_to_kml)

    placemark_b = placemarks[-1]
    placemarks.pop()
    placemarks.insert(1, placemark_b)

    segment = 1

    for placemark in placemarks:
        # kep track of time
        # placemark.coords = placemark.coords[:60]

        print(f"[{placemark.name}] Fetching data...")
        # convert elevation to meters
        route_data: list[tuple[float, float, float, float, float, float]] = list(
            map(
                lambda p: (
                    p.lat,
                    p.lon,
                    calc_distance(placemark.coords, p),
                    calc_azimuth(placemark.coords, p),
                    p.elevation * 0.3048,
                    0,
                ),
                placemark.coords,
            )
        )
        weather_data: list[tuple[int, int, int]] = get_irradiance_and_wind_data(
            placemark.coords, current_time
        )

        # assert len(weather_data) == len(route_data)

        db_data: list[
            tuple[float, float, float, float, float, float, int, int, int]
        ] = []
        for i in range(len(route_data)):
            db_data.append(
                (
                    route_data[i][0],
                    route_data[i][1],
                    route_data[i][2],
                    0,
                    route_data[i][3],
                    route_data[i][4],
                    weather_data[i][0],
                    weather_data[i][1],
                    weather_data[i][2],
                )
            )

        data = data_rows(segment, db_data)
        cursor.executemany(
            "insert into route_data values (?,?,?,?,?,?,?,?,?,?,?)", data
        )

        with open(
            "src/limits/" + placemark.name + " Limits.csv", newline=""
        ) as csvfile:
            reader = csv.reader(csvfile)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]

        for distance, speed in speed_limits:
            cursor.execute(
                """
            UPDATE route_data
            SET speed_limit = ?
            WHERE distance >= ?
                AND (distance < ? OR ? = (SELECT MAX(distance) FROM route_data WHERE segment_id = ?))
                AND segment_id = ?
            """,
                (
                    speed,
                    distance,
                    (
                        speed_limits[speed_limits.index((distance, speed)) + 1][0]
                        if speed_limits.index((distance, speed)) + 1 < len(speed_limits)
                        else float("inf")
                    ),
                    distance,
                    segment,
                    segment,
                ),
            )

        segment += 1

        print(f"[{placemark.name}] Inserted into database!")

# 2 also make the kml file stuff work dynamically, ie work when run from base directory
def init_route_table(connection, cursor):
    create = """
    create table route_data (
        segment_id integer not null,
        id integer not null,
        lat float not null,
        lon float not null,
        distance float not null,
        speed_limit float not null,
        azimuth float not null,
        elevation float not null,
        ghi int not null,
        wind_dir float not null,
        wind_speed float not null,
        PRIMARY KEY (segment_id, id)
    );
    """

    cursor.execute(create)
    generate_data("data/Main Route.kml", datetime.datetime.now(), cursor)

    connection.commit()

# 1
if __name__ == "__main__":
    connection = sqlite3.connect("data.sqlite")
    cursor = connection.cursor()
    init_route_table(connection, cursor)