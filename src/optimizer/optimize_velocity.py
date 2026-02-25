from __future__ import annotations
import time
from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.interval_simulator import SSInterval, join_intervals
from ..engine.kinematics import Speed
import numpy as np
from itertools import product

def optimize_velocity(placemark_name: str = "A. Independence to Topeka", db_path: str = "ASC_2024.sqlite", max_nodes: int = 100):
    intervals = fetch_route_intervals(placemark_name, split_at_stops=True, max_nodes=max_nodes, db_path=db_path)
    print(f"Fetched {len(intervals)} intervals for optimization")

    produce_options(1, 4, 1, 10)

def produce_options(start: float, stop: float, step: float, num_segments):
    # Placeholder for the actual optimization logic
    start_time = time.time()
    speeds = np.arange(start, stop + step, step)
    combos = list(product(speeds, repeat=num_segments))
    for combo in combos:
        # print(combo)
        pass
    print(f"Generated {len(combos)} speed combinations for optimization")
    print(f"Time taken to generate combinations: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    optimize_velocity()