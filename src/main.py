import sqlite3
from pytz import timezone
import time
import datetime
from .engine.kinematics import Coordinate, Speed
from .engine.interval_simulator import SSInterval  # Adjust as needed
from .engine.nodes import Segment
from .database.init_route_table import init_route_db
from .database.fetch_route_intervals import fetch_route_intervals
from .database.update_velocity import update_target_velocity

def main():
    start = time.time()
    init_route_db(remake= False, update_traffic_data= False)
    print(f"Finished creating Database: {time.time()-start}")

    current_tz = timezone("US/Eastern")
    current_time: datetime = datetime.datetime.now(tz=current_tz)
    intervals = fetch_route_intervals("A. Independence to Topeka", split_at_stops=True, max_nodes=None)
    for i in range(min(3, len(intervals))):
        print(f"Simulating Interval {i+1} of {len(intervals)}")
        intervals[i].simulate_interval()
        intervals[i].plot("dist", ["speed.kmph", "segment.speed_limit.kmph", "segment.v_eff.kmph"], "velocity_comparison")
        # intervals[i].plot("dist", ["speed.kmph"], f"interval_{i+1}_velocity")
    print(f"Completed Display: {time.time()-start}")
    
    import matplotlib.pyplot as plt
    plt.show()
    input()



if __name__ == "__main__":
    main()