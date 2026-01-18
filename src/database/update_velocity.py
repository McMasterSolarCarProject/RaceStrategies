import sqlite3
import time
import os
from ..engine.kinematics import Coordinate, Speed, Velocity, Displacement
from ..engine.nodes import Segment, VelocityNode, NULL_VELOCITY_NODE
from ..engine.velocity_simulator import simulate_speed_profile
from .fetch_route_intervals import fetch_route_intervals


def update_target_velocity(segment_id):
    interval = fetch_route_intervals(segment_id)
    for segment in interval.segments:
        nodes = simulate_speed_profile(segment, max_speed_lim=segment.speed_limit)
        upload_best_velocity(nodes, segment_id, segment.id)

def upload_best_velocity(nodes: list[VelocityNode], segment_id, id):
    # for now just pick one with epm of 100
    if not nodes:
        print(f"No velocity nodes generated for segment {segment_id} id {id}")
        return

    emp_target = 100
    min_dist = 10000
    best_node = nodes[0]
    for node in nodes:
        if node.epm <= 0:
            # print("Skipping node with non-positive epm")
            continue
        if abs(emp_target - node.epm) < min_dist:
            best_node = node
            min_dist = abs(emp_target - node.epm)
            if min_dist < 1: # correct this so it uses some units
                 break
    
    if best_node:
        db_path = 'data.sqlite'
        if not os.path.exists(db_path):
            print(f"Database file '{db_path}' does not exist. Skipping database update.")
            return
        
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        # add power here
        cursor.execute('UPDATE route_data SET speed = ?, torque = ? WHERE segment_id = ? AND id = ?', (best_node.speed.kmph, best_node.torque, segment_id, id))

        db.commit()
        db.close()
    else:
        raise ValueError(f"could not find Velocity Node with epm of {emp_target}, speed {best_node.speed.kmph}, torque {best_node.torque}")


if __name__ == "__main__":
    print("Started Velocity Update")
    start = time.time()
    update_target_velocity("A. Independence to Topeka")
    print(f"Finished updating velocity and torque values: {time.time()-start}")