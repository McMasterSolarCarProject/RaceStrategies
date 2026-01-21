from ..engine.kinematics import Vec, Coordinate, Speed, Velocity
from ..engine.nodes import Segment
from ..engine.interval_simulator import SSInterval
import sqlite3

#RENAME TO FETCH_ROUTE_INTERVALS

def fetch_route_intervals(placemark: str, split_at_stops: bool = False, max_nodes: int = None) -> list[SSInterval] | SSInterval:
    conn = sqlite3.connect("data.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_data WHERE segment_id = ? ORDER BY id"
    cursor.execute(query, (placemark,))
    rows = cursor.fetchall()

    ssintervals = []
    segments = []
    # print(f"Total rows: {len(rows)}, split_at_stops: {split_at_stops}")
    max_nodes = min(max_nodes, len(rows)) if max_nodes is not None else len(rows)
    for i, checkpoint in enumerate(rows[:max_nodes-1]):
        segments.append(create_segment(checkpoint, rows[i+1]))
        # print(f"Row {i}: stop_type={checkpoint['stop_type']}")

        if rows[i+1]["stop_type"] and split_at_stops:
            print(f"  -> Splitting at row {i+2}, id {i+1}, stop_type={rows[i+1]['stop_type']}")
            ssintervals.append(SSInterval(segments))
            segments = []

    if segments:
        ssintervals.append(SSInterval(segments))
        
    cursor.close()
    conn.close()
    # print(f"{len(ssintervals[0].segments)} segments in the first interval")
    return ssintervals if split_at_stops else ssintervals[0]


def parse_segment(placemark, checkpoint):
    conn = sqlite3.connect("data.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_data WHERE segment_id = ? AND id IN (?, ?) ORDER BY id"
    cursor.execute(query, (placemark, checkpoint, checkpoint + 1))
    rows = cursor.fetchall()
    if len(rows) != 2:
        print("Invalid amount of rows taken")

    segment = create_segment(rows[0], rows[1])

    cursor.close()
    conn.close()

    return segment

def create_segment(checkpoint: sqlite3.Row, next_checkpoint: sqlite3.Row) -> Segment:
    current_coord = Coordinate(checkpoint["lat"], checkpoint["lon"], checkpoint["elevation"])
    next_coord = Coordinate(next_checkpoint["lat"], next_checkpoint["lon"], next_checkpoint["elevation"])
    # wind = Velocity(Vec(checkpoint["wind_dir"]), Speed(kmph=checkpoint["wind_speed"]))
    wind = Velocity()
    return Segment(current_coord, next_coord, checkpoint["id"],Speed(kmph=checkpoint["speed_limit"]), checkpoint["ghi"], wind, Speed(kmph= checkpoint["speed"]), checkpoint["torque"])

if __name__ == "__main__":
    # intervals = fetch_route_intervals("A. Independence to Topeka")
    # for segment in intervals[0].segments:
    #     print(segment)
    seg = parse_segment("A. Independence to Topeka", 1)
    print(seg)
    # for segment in ssInterval.segments:
    #     print(segment)

