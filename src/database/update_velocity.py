import sqlite3
import time
import os
from ..engine.nodes import StateNode
from ..engine.velocity_simulator import simulate_speed_profile, choose_closest_epm_node
from .fetch_route_intervals import fetch_route_intervals


def update_target_velocity(placemark_name: str, db_path: str = "ASC_2024.sqlite") -> None:
    route_interval = fetch_route_intervals(placemark_name)
    for segment in route_interval.segments:
        velocity_nodes = simulate_speed_profile(segment, max_speed_lim=segment.speed_limit)
        upload_best_velocity(velocity_nodes, placemark_name, segment.id, db_path)

def upload_best_velocity(nodes: list[StateNode], placemark_name: str, id: int, db_path: str = "ASC_2024.sqlite"):
    if len(nodes) == 0:
        print(f"No velocity nodes generated for segment {placemark_name} id {id}")
        return

    epm_target = 100
    best_node = choose_closest_epm_node(nodes, epm_target)
    if best_node is None:
        print(f"No valid velocity candidate for segment {placemark_name} id {id}")
        return
    
    if best_node:
        if not os.path.exists(db_path):
            print(f"Database file '{db_path}' does not exist. Skipping database update.")
            return
        
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        # add power here
        cursor.execute('UPDATE route_row SET speed = ?, torque = ? WHERE placemark_name = ? AND id = ?', (best_node.speed.kmph, best_node.torque, placemark_name, id))

        db.commit()
        db.close()
    else:
        raise ValueError(f"could not find Velocity Node with epm of {epm_target}, speed {best_node.speed.kmph}, torque {best_node.torque}")


if __name__ == "__main__":
    print("Started Velocity Update")
    start = time.time()
    update_target_velocity("A. Independence to Topeka")
    print(f"Finished updating velocity and torque values: {time.time()-start}")
