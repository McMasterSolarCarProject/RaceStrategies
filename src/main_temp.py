import sqlite3


def get_route(segment_id):
    conn = sqlite3.connect("data.sqlite")
    cursor = conn.cursor()

    query = """
    SELECT segment_id, lat, lon, distance, azimuth, elevation, ghi, wind_dir, wind_speed, speed_limit FROM route_data
    WHERE segment_id = ?
    ORDER BY id
    """
    cursor.execute(query, (segment_id,))


    results = cursor.fetchall()
    # if results:
    #     print(f"Route for segment {segment_id}:")
    #     for result in results:
    #         print(f"ID: {result[0]}, Azimuth: {result[1]} degrees, Elevation: {result[2]} meters, Distance: {result[3]} meters")
    # else:
    #     print("No data found for the specified segment.")

    checkpoints = []
    for result in results:
        checkpoints.append(Checkpoint(
            result[1],
            result[2],
            result[3],
            result[4],
            result[5],
            result[6],
            result[7],
            result[8],
            result[9],
        ))

    cursor.close()
    conn.close()

    return Route(result[0], checkpoints)


class Checkpoint:
    def __init__(
        self,
        lat: float,
        lon: float,
        distance: float,
        azimuth: float,
        elevation: float,
        ghi: int,
        wind_dir: float,
        wind_speed: float,
        speed_limit: float
    ):
        self.lat = lat
        self.lon = lon
        self.distance = distance
        self.azimuth = azimuth
        self.elevation = elevation
        self.ghi = ghi
        self.wind_dir = wind_dir
        self.wind_speed = wind_speed
        self.speed_limit = speed_limit

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.wind_dir} | Wind Speed: {self.wind_speed} | Speed Limit: {self.speed_limit}"

    def __repr__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.wind_dir} | Wind Speed: {self.wind_speed} | Speed Limit: {self.speed_limit}"


class Route:
    def __init__(self, name: str, checkpoints: list[Checkpoint]):
        self.name = name
        self.checkpoints = checkpoints

    def __str__(self):
        return f"{self.name}: {self.checkpoints}"

    def __repr__(self):
        return f"{self.name}: {self.checkpoints}"

from .engine.kinematics import Coordinate, Displacement, Velocity, Segment
from .engine.interval_simulator import SSInterval  # Adjust as needed


def route_to_ssinterval(route: Route, default_power: float = 275) -> SSInterval:
    """
    Converts a Route object into an SSInterval.

    Args:
        route (Route): Route object containing checkpoints
        default_power (float): Default power to assign to each Segment

    Returns:
        SSInterval: A simulation interval ready for physics calculations
    """
    segments = []
    checkpoints = route.checkpoints

    for i in range(len(checkpoints) - 1):
        c1 = checkpoints[i]
        c2 = checkpoints[i + 1]

        p1 = Coordinate(c1.lon, c1.lat, c1.elevation)  # Note: lon, lat ordering!
        p2 = Coordinate(c2.lon, c2.lat, c2.elevation)

        disp = Displacement(p1, p2)

        velocity = Velocity(disp.unit_vector(), kmph=c1.speed_limit)  # Or average with c2?

        segment = Segment(p1, p2, velocity, default_power)  # you can make power dynamic if needed
        segments.append(segment)

    return SSInterval(segments)