import sqlite3
import time
from ..engine.kinematics import Coordinate, Speed, Velocity, Displacement
from ..engine.nodes import Segment, VelocityNode, NULL_VELOCITY_NODE
from ..engine.velocity_simulator import simulate_speed_profile
from .parse_route_table import parse_route_table


def update_target_velocity(segment_id):
    interval = parse_route_table(segment_id)
    for segment in interval.segments:
        nodes = simulate_speed_profile(segment, max_speed_lim=segment.speed_limit)
        print('adam')
        upload_best_velocity(nodes, segment_id, segment.id)

def upload_best_velocity(nodes: list[VelocityNode], segment_id, id):
    # for now just pick one with epm of 100

    emp_target = 100
    min_dist = 10000
    best_node = nodes[0] if nodes else NULL_VELOCITY_NODE
    for node in nodes:
        # print(node.epm, node.velocity.kmph)
        if node.epm <=0:
            pass
        if abs(emp_target-node.epm) < min_dist:
            best_node = node
            min_dist = abs(emp_target-node.epm)
            if min_dist < 1:
                 break
    if best_node.speed.kmph:
        # store in db
        print(best_node.epm, best_node.speed.kmph)
        db = sqlite3.connect('data.sqlite')
        cursor = db.cursor()
        # add power here
        cursor.execute('UPDATE route_data SET speed = ?, torque = ? WHERE segment_id = ? AND id = ?', (best_node.speed.kmph, best_node.torque,segment_id, id))

        db.commit()
        db.close()
    else:
        raise ValueError(f"could not find Velocity Node with epm of {emp_target}")


if __name__ == "__main__":
    start = time.time()
    update_target_velocity("A. Independence to Topeka")
    print(time.time()-start)