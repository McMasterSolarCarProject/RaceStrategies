import sqlite3
from pytz import timezone
import time
import datetime

from src.database.traffic import update_traffic
from .engine.kinematics import Coordinate, Speed
from .engine.interval_simulator import SSInterval  # Adjust as needed
from .engine.nodes import Segment
from .database import  fetch_route_intervals


def main():
    start = time.perf_counter()
    # update_traffic("A. Independence to Topeka")
    # init_route_db(remake= False)
    # # # placemarks = ["A. Independence to Topeka"]
    # placemarks = parse_kml_file()
    # for placemark in placemarks:
    #     if True:  # Set to True to update velocity data
    #         # print(f"Updating velocity data for {placemark}")
    #         upload_speed_limit(placemark)
    #         update_target_velocity(placemark)
    #         # update_traffic(placemark)
    # print(f"Finished creating Database: {time.perf_counter()-start}")


    # current_tz = timezone("US/Eastern")
    # current_time: datetime = datetime.datetime.now(tz=current_tz)

    intervals = fetch_route_intervals("A. Independence to Topeka", split_at_stops=True, max_nodes=None, db_path="ASC_2024.sqlite")
    intervals = [intervals] if type(intervals) is SSInterval else intervals
    print(len(intervals))
    intervals = intervals
    for i in range(min(10000, len(intervals))):
        print(f"Simulating Interval {i+1} of {len(intervals)}")
        intervals[i].simulate_interval()
        intervals[i].plot("dist", ["speed.kmph", "segment.speed_limit.kmph"], "velocity_comparison")
        # intervals[i].plot("dist", ["speed.kmph"], f"interval_{i+1}_velocity")
    print(f"Completed Display: {time.perf_counter()-start}")
    
    import matplotlib.pyplot as plt
    plt.show()
    input()



if __name__ == "__main__":
    main()