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
from .database.traffic import update_traffic

def main():
    start = time.perf_counter()
    init_route_db(remake= False, update_traffic_data= False, update_velocity= False)
    placemarks = ["A. Independence to Topeka"]  # Add more placemarks as needed
    for placemark in placemarks:
        if False:  # Set to True to update velocity data
            print(f"Updating velocity data for {placemark}")
            update_target_velocity(placemark)
            update_traffic(placemark)
    print(f"Finished creating Database: {time.perf_counter()-start}")

    current_tz = timezone("US/Eastern")
    current_time: datetime = datetime.datetime.now(tz=current_tz)
    intervals = fetch_route_intervals("A. Independence to Topeka", split_at_stops=True, max_nodes=1000)
    print(len(intervals))
    intervals = intervals
    for i in range(min(1000, len(intervals))):
        print(f"Simulating Interval {i+1} of {len(intervals)}")
        intervals[i].simulate_interval()
        intervals[i].plot("dist", ["speed.kmph", "segment.speed_limit.kmph", "segment.v_eff.kmph"], "velocity_comparison")
        # intervals[i].plot("dist", ["speed.kmph"], f"interval_{i+1}_velocity")
    print(f"Completed Display: {time.perf_counter()-start}")
    
    import matplotlib.pyplot as plt
    plt.show()
    input()



if __name__ == "__main__":
    main()