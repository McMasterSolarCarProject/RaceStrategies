import sqlite3
import time
from ..engine.kinematics import Coordinate, Speed, Velocity, Displacement
from ..engine.nodes import Segment
from ..engine.velocity_simulator import sim_velocity_an_shi
from .parse_route_table import parse_route_table


def update_target_velocity(segment_id):
    interval = parse_route_table(segment_id)
    for segment in interval.segments:
        nodes = sim_velocity_an_shi(segment, segment.speed_limit)
        upload_best_velocity(nodes, segment_id, segment.id)

def upload_best_velocity(nodes, segment_id, id):
    # for now just pick one with epm of 100

    emp_target = 100
    min_dist = 10000
    best_node = nodes[0]
    for node in nodes:
        # print(node.epm, node.velocity.kmph)
        if node.epm <=0:
            pass
        if abs(emp_target-node.epm) < min_dist:
            best_node = node
            min_dist = abs(emp_target-node.epm)
            if min_dist < 1:
                 break
    if best_node.velocity.kmph != 0:
        # store in db
        print(best_node.epm, best_node.velocity.kmph)
        db = sqlite3.connect('data.sqlite')
        cursor = db.cursor()
        # add power here
        cursor.execute('UPDATE route_data SET speed = ?, power = ? WHERE segment_id = ? AND id = ?', (best_node.velocity.kmph, best_node.torque,segment_id, id))

        db.commit()
        db.close()
    else:
        raise ValueError(f"could not find Velocity Node with epm of {emp_target}")


if __name__ == "__main__":
    start = time.time()
    update_target_velocity("A. Independence to Topeka")
    print(time.time()-start)