from ..engine.kinematics import Vec, Coordinate, Speed, Velocity
from ..engine.nodes import Segment
from ..engine.interval_simulator import SSInterval
import sqlite3

def parse_route_table(placemark, stops: bool = False):
    conn = sqlite3.connect("data.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_data WHERE segment_id = ? ORDER BY id"
    cursor.execute(query, (placemark,))
    rows = cursor.fetchall()

    ssintervals = []
    segments = []
    for i, checkpoint in enumerate(rows[:-1]):
        current_coord = Coordinate(checkpoint["lat"], checkpoint["lon"], checkpoint["elevation"])
        next_coord = Coordinate(rows[i+1]["lat"], rows[i+1]["lon"], rows[i+1]["elevation"])
        # wind = Velocity(Vec(checkpoint["wind_dir"]), Speed(kmph=checkpoint["wind_speed"]))
        wind = Velocity()
        segments.append(Segment(current_coord, next_coord, checkpoint["id"],Speed(kmph=checkpoint["speed_limit"]), checkpoint["ghi"], wind, Speed(kmph= checkpoint["speed"]), checkpoint["torque"]))
        if rows[i+1]["stop_type"] and stops:
            ssintervals.append(SSInterval(segments))
            segments = []

    cursor.close()
    conn.close()
    if stops: return ssintervals
    return SSInterval(segments)

if __name__ == "__main__":
    ssInterval = parse_route_table("A. Independence to Topeka")
    for segment in ssInterval.segments:
        print(segment)

