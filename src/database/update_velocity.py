import sqlite3
import math
from ..engine.kinematics import Coordinate, Speed, Velocity, Displacement
from ..engine.nodes import Segment
from ..engine.velocity_simulator import sim_velocity_an_shi


def update_target_velocity(segment_id):
    segments = get_route(segment_id)
    for segment in segments:
        nodes = sim_velocity_an_shi(segment)
        upload_best_velocity(nodes, segment_id)

def get_route(segment_id):
    conn = sqlite3.connect("data.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM route_data WHERE segment_id = ? ORDER BY id"
    cursor.execute(query, (segment_id,))
    rows = cursor.fetchall()
    # print(rows)
    dist = 0
    segments = []
    for i, checkpoint in enumerate(rows[:-1]):
        current_coord = Coordinate(checkpoint["lat"], checkpoint["lon"], 0) #checkpoint["elevation"]
        next_coord = Coordinate(rows[i+1]["lat"], rows[i+1]["lon"],0) #rows[i+1]["elevation"]
        d = Displacement(current_coord, next_coord)
        dist += (d.dist)
        speed_lim = Speed(kmph=checkpoint["speed_limit"])
        wind = Velocity(d.unit_vector(), Speed(rows[i]["wind_speed"]))
        segments.append(Segment(current_coord, next_coord, speed_lim, wind))
        print(f"Object Dist: {d.dist}, Haversine Dist: {rows[i+1]["distance"]}, Diff: {dist - rows[i+1]["distance"]}")

    cursor.close()
    conn.close()

    return segments

def upload_best_velocity(nodes, segment_id):
    # for now just pick one with epm of 100

    emp_target = 0
    min_dist = 10000
    best_velocity = 0 
    for node in nodes:
        # print(node.epm, node.velocity.mph)
        if abs(emp_target-node.epm) < min_dist:
            best_velocity = node.velocity
            min_dist = abs(emp_target-node.epm)
            if min_dist < 1:
                 break

    if best_velocity != 0:
        # store in db
        db = sqlite3.connect('data.sqlite')
        cursor = db.cursor()
        cursor.execute('UPDATE route_data SET speed = ? WHERE segment_id = ?', (best_velocity.mph, segment_id))

        db.commit()
        db.close()
    else:
        raise ValueError(f"could not find Velocity Node with epm of {emp_target}")


if __name__ == "__main__":
    # update_target_velocity("A. Independence to Topeka")
    coords = get_route("A. Independence to Topeka")
    # p1 = coords[0].p1
    # p2 = coords[0].p2
    # # CURRENTLY TESTING THE DIFFERENCE BETWEEN DISTANCE CALCS
    # from .parse_route import heversine_and_azimuth
    # distance, _ = heversine_and_azimuth(p1.lon, p1.lat, p2.lon, p2.lat)
    # print(distance*1000)
    # print(coords[0].p1, coords[0].p2, coords[0].dist)