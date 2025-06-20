import sqlite3

from .engine.kinematics import Coordinate, Displacement, Velocity, Speed
from .engine.interval_simulator import SSInterval  # Adjust as needed

def get_route(segment_id):
    conn = sqlite3.connect("data.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_data WHERE segment_id = ? ORDER BY id"
    cursor.execute(query, (segment_id,))
    rows = cursor.fetchall()

    segments = []
    for i, checkpoint in enumerate(rows[:-1]):
        current_coord = Coordinate(checkpoint["lat"], checkpoint["lon"], checkpoint["elevation"])
        next_coord = Coordinate(rows[i+1]["lat"], rows[i+1]["lon"], rows[i+1]["elevation"])
        segments.append(Segment(current_coord, next_coord, Speed(kmph=checkpoint["speed_limit"])))

    cursor.close()
    conn.close()

    return SSInterval(segments)


class Checkpoint: #just like a coordinate
    def __init__(self, lat: float, lon: float, distance: float, elevation: float, ghi: int,
                 wind_dir: float, wind_speed: float, speed_limit: float):
        self.lat = lat
        self.lon = lon
        self.elevation = elevation
        self.distance = distance
        self.azimuth = azimuth
        self.ghi = ghi
        self.wind_dir = wind_dir
        self.wind_speed = wind_speed
        self.speed_limit = speed_limit

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.wind_dir} | Wind Speed: {self.wind_speed} | Speed Limit: {self.speed_limit}"

    def __repr__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.wind_dir} | Wind Speed: {self.wind_speed} | Speed Limit: {self.speed_limit}"


class Route: # literally a list of coordinates
    def __init__(self, name: str, checkpoints: list[Checkpoint]):
        self.name = name
        self.checkpoints = checkpoints

    def __str__(self):
        return f"{self.name}: {self.checkpoints}"

    def __repr__(self):
        return f"{self.name}: {self.checkpoints}"


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