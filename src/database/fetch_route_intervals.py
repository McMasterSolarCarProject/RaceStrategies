import sqlite3

import numpy as np

from ..engine.interval_simulator import RouteInterval
from ..engine.nodes import Segment
from .route_row import RouteRow


def fetch_route_intervals(placemark_name: str, split_at_stops: bool = False, max_nodes: int = None, db_path: str = "ASC_2024.sqlite") -> list[RouteInterval] | RouteInterval:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_row WHERE placemark_name = ? ORDER BY id"
    cursor.execute(query, (placemark_name,))
    rows = cursor.fetchall()
    route_rows = [RouteRow.from_sql_row(r) for r in rows]

    route_intervals = []
    segments = []
    target_profile_rows = []
    # print(f"Total rows: {len(route_rows)}, split_at_stops: {split_at_stops}")
    max_nodes = min(max_nodes, len(route_rows)) if max_nodes is not None else len(route_rows)
    for i, checkpoint in enumerate(route_rows[:max_nodes-1]):
        segments.append(checkpoint.to_segment(route_rows[i+1]))
        target_profile_rows.append(checkpoint.to_target_profile_row())

        if route_rows[i+1].stop_type and split_at_stops:
            print(f"  -> Splitting at row {i+2}, id {i+1}, stop_type={route_rows[i+1].stop_type}")
            route_intervals.append(RouteInterval(segments, target_profile=np.array(target_profile_rows, dtype=float)))
            segments = []
            target_profile_rows = []

    if segments:
        route_intervals.append(RouteInterval(segments, target_profile=np.array(target_profile_rows, dtype=float)))
        
    cursor.close()
    conn.close()
    return route_intervals if split_at_stops else route_intervals[0]


def fetch_segment(placemark_name: str, checkpoint, db_path: str = "ASC_2024.sqlite") -> Segment:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_row WHERE placemark_name = ? AND id IN (?, ?) ORDER BY id"
    cursor.execute(query, (placemark_name, checkpoint, checkpoint + 1))
    rows = cursor.fetchall()
    if len(rows) != 2:
        print("Invalid amount of rows taken")

    route_rows = [RouteRow.from_sql_row(r) for r in rows]
    segment = route_rows[0].to_segment(route_rows[1])

    cursor.close()
    conn.close()

    return segment





if __name__ == "__main__":
    # intervals = fetch_route_intervals("A. Independence to Topeka")
    # for segment in intervals[0].segments:
    #     print(segment)
    seg = fetch_segment("A. Independence to Topeka", 1)
    print(seg)
    # for segment in RouteInterval.segments:
    #     print(segment)
